from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status
import bcrypt
from pydantic import BaseModel
from keycloak import KeycloakOpenID
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
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
import requests
from starlette.status import (
    HTTP_200_OK,
    HTTP_401_UNAUTHORIZED,
    HTTP_500_INTERNAL_SERVER_ERROR
)

from joeseln_backend.services.sessiontoken.session_token_service import \
    TokenService
from joeseln_backend.conf.base_conf import STATIC_ADMIN_TOKEN, \
    KEYCLOAK_CLIENT_ID, KEYCLOAK_CLIENT_SECRET, KEYCLOAK_REALM_NAME, \
    KEYCLOAK_SERVER_URL

keycloak_openid = KeycloakOpenID(server_url=KEYCLOAK_SERVER_URL,
                                 client_id=KEYCLOAK_CLIENT_ID,
                                 realm_name=KEYCLOAK_REALM_NAME,
                                 client_secret_key=KEYCLOAK_CLIENT_SECRET)

from joeseln_backend.mylogging.root_logger import logger

SECRET_KEY = "b014bc552ecfc62a46b6c4bea9d35d6d7e5ff6f0244eff28a3f5ad4be1d3015d"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 20
ACCESS_TOKEN_EXPIRE_SECONDS = 1000


class Token(BaseModel):
    access_token: str
    token_type: str


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


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    TokenService.set_token_exp(token=encoded_jwt.decode(),
                               exp=int(expire.strftime("%Y%m%d%H%M%S")))
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
        # logger.info(e)
        if Security.check_token_exp(token.encode().decode()):
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM],
                                 leeway=36000)
            # we aligned to keycloak's sub
            username: str = payload.get("sub")
            if username is None:
                return
            user = get_user_with_groups_by_uname(db=SessionLocal(),
                                                 username=username)

            if user is None:
                return
            return user
        else:
            logger.info('token expired ')
            return

    except jwt.exceptions.PyJWTError as e:
        logger.error(f'PyJWTError: {e}')
        return


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    _jwt_error = None
    # try as non oidc user
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
        # logger.info(e)
        if Security.check_token_exp(token.encode().decode()):
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM],
                                 leeway=36000)
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
        else:
            logger.info('token expired ')
            raise credentials_exception

    except jwt.exceptions.PyJWTError as e:
        logger.error(f'oidc user is considered as non oidc user: {e}')
        _jwt_error = e

    # try as oidc user

    try:
        token_info = keycloak_openid.introspect(token)
    except:
        return

    if token_info['active']:
        # TODO for a better performance this could be called only at /users/me
        user = update_oidc_user(db=SessionLocal(),
                                oidc_user=OIDCUserCreate.parse_obj(token_info))
        if user:
            update_oidc_user_groups(db=SessionLocal(), user=user)
            user = get_user_with_groups_by_uname(db=SessionLocal(),
                                                 username=user.username)
        if user is None or user.deleted:
            raise credentials_exception
        return user

    elif not token_info['active']:
        return None
    elif _jwt_error:
        raise credentials_exception
    else:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Internal authentication error (our bad)'
        )


async def get_current_jwt_user_for_ws(token):
    try:
        jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return True
    except jwt.exceptions.PyJWTError:
        return


async def get_current_keycloak_user_for_ws(token):
    try:
        token_info = keycloak_openid.introspect(token)
    except:
        return
    if token_info['active']:
        return True
    return


class Security:
    @staticmethod
    def create_password(password):
        bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        hash = bcrypt.hashpw(bytes, salt)
        logger.info(hash)

    @staticmethod
    def check_password(username, password):
        hash = Security.get_hashed_password(username=username)
        userBytes = password.encode('utf-8')
        result = bcrypt.checkpw(userBytes, hash)
        logger.info(result)

    @staticmethod
    def get_hashed_password(username):
        foo = 'foo'
        return foo.encode()

    @staticmethod
    def check_token_exp(token):
        exp = TokenService.get_token_exp(token=token)
        if exp < int(datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")):
            return False
        else:
            TokenService.extend_token(token=token)
            return True
