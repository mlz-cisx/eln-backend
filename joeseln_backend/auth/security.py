from cachetools import cached, TTLCache
from sqlalchemy import false
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status
import bcrypt
from pydantic import BaseModel
from joeseln_backend.database.database import SessionLocal
from joeseln_backend.conf.base_conf import INSTRUMENT_AS_ADMIN
from joeseln_backend.services.user.user_service import update_oidc_user, \
    get_user_by_uname
from joeseln_backend.services.user.user_schema import OIDCUserCreate
from joeseln_backend.services.user_to_group.user_to_group_service import \
    get_user_with_groups_by_uname, update_oidc_user_groups

from typing import Annotated, Any
from datetime import datetime, timedelta, timezone
import jwt
import time
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
import requests
from starlette.status import (
    HTTP_200_OK,
    HTTP_401_UNAUTHORIZED,
    HTTP_500_INTERNAL_SERVER_ERROR
)

from joeseln_backend.conf.base_conf import STATIC_ADMIN_TOKEN

from joeseln_backend.mylogging.root_logger import logger

SECRET_KEY = "b014bc552ecfc62a46b6c4bea9d35d6d7e5ff6f0244eff28a3f5ad4be1d3015d"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 20
ACCESS_TOKEN_EXPIRE_SECONDS = 1000
DOWNLOAD_TOKEN_EXPIRE_MINUTES = 60 * 24


class Token(BaseModel):
    access_token: str
    token_type: str | None = None


class TokenData(BaseModel):
    username: str | None = None


class User(BaseModel):
    username: str
    email: str | None = None
    full_name: str | None = None
    disabled: bool | None = None
    # we align to keycloak's realm access
    realm_access: Any | None = None


class UserInDB(User):
    hashed_password: str


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def get_user(db, username: str):
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)


def get_user_without_pw_hash(db, username: str):
    if username in db:
        user_dict = db[username]
        return User(**user_dict)


def _authenticate_user(fake_db, username: str, password: str):
    user = get_user(fake_db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


def authenticate_user(db: Session, username: str, password: str):
    user = get_user_by_uname(db, username)
    if not user:
        return False
    if not verify_password(password, user.password):
        return False
    return user

# token used to donwload picture and file
token_cache = {}
def invalidate_download_token(user):
    cache_key = user.username
    if cache_key in token_cache:
        del token_cache[cache_key]

def build_download_token(user):
    current_time = time.time()
    cache_key = user.username
    access_token = None

    # Check if a valid token exists in the cache
    if cache_key in token_cache:
        token, expires_at = token_cache[cache_key]
        if current_time < expires_at:
            access_token = token
        else:
            del token_cache[cache_key]

    # Generate a new token if none exists or the existing one is expired
    if not access_token:
        access_token_expires = timedelta(
            minutes=DOWNLOAD_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )
        expires_at = current_time + access_token_expires.total_seconds()
        token_cache[cache_key] = (access_token, expires_at)

    return access_token


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_user_from_jwt(token: Annotated[str, Depends(oauth2_scheme)]):
    try:
        if token == STATIC_ADMIN_TOKEN:
            # logger.info('you can do everything')
            user = get_user_by_uname(db=SessionLocal(),
                                     username=INSTRUMENT_AS_ADMIN)
            return user
        else:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            # we aligned to keycloak's sub
            username: str = payload.get("sub")
            if username is None:
                return
            user = get_user_with_groups_by_uname(db=SessionLocal(),
                                                 username=username)
            if user is None:
                return
            return user
    except jwt.exceptions.ExpiredSignatureError as e:
        # logger.info('token expired ')
        return

    except jwt.exceptions.PyJWTError as e:
        logger.error(f'PyJWTError: {e}')
        return

@cached(cache=TTLCache(maxsize=1024, ttl=120))
def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        if token == STATIC_ADMIN_TOKEN:
            # logger.info('you can do everything')
            user = get_user_with_groups_by_uname(db=SessionLocal(),
                                                 username=INSTRUMENT_AS_ADMIN)
            return user
        else:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            # we aligned to keycloak's sub
            username: str = payload.get("sub")
            if username is None:
                raise credentials_exception
            # TODO for a better performance this could be called only at /users/me
            user = get_user_with_groups_by_uname(db=SessionLocal(),
                                                 username=username)
            if user is None or user.deleted:
                raise credentials_exception
            return user
    except jwt.exceptions.ExpiredSignatureError as e:
        # logger.info('token expired ')
        raise credentials_exception

    except jwt.exceptions.PyJWTError as e:
        logger.error(f'oidc user is considered as non oidc user: {e}')


def verify_jwt_with_leeway(token, leeway=300):
    payload  = jwt.decode(token.access_token.encode(), SECRET_KEY, algorithms=[ALGORITHM], leeway=leeway)
    username = payload.get("sub")
    return username

async def get_current_jwt_user_for_ws(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        uname: str = payload.get("sub")
        return uname
    except jwt.exceptions.PyJWTError:
        return

