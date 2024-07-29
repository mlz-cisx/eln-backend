from fastapi import Depends, HTTPException, status
import bcrypt
from pydantic import BaseModel
from joeseln_backend.database.database import SessionLocal
from joeseln_backend.services.user.user_service import update_oidc_user
from joeseln_backend.services.user.user_schema import OIDC_User_Create

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
from joeseln_backend.conf.base_conf import KEYCLOAK_BASEURL, STATIC_ADMIN_TOKEN

from joeseln_backend.mylogging.root_logger import logger

SECRET_KEY = "b014bc552ecfc62a46b6c4bea9d35d6d7e5ff6f0244eff28a3f5ad4be1d3015d"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1
ACCESS_TOKEN_EXPIRE_SECONDS = 1000

fake_users_db = {
    "johndoe": {
        "username": "johndoe",
        "full_name": "John Doe",
        "email": "johndoe@example.com",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
        "disabled": False,
        "realm_access": {
            "roles": ["MyProject1", "MyProject2"]
        }
    },
    "admin": {
        "username": "admin",
        "full_name": "Super Admin",
        "email": "admin@example.com",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
        "disabled": False,
    }
}


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
    realm_access: Any | None



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


def authenticate_user(fake_db, username: str, password: str):
    user = get_user(fake_db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
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
            user = get_user_without_pw_hash(fake_users_db, username='admin')
            return user
        else:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            # we aligned to keycloak's sub
            username: str = payload.get("sub")
            if username is None:
                raise credentials_exception
            token_data = TokenData(username=username)
            user = get_user_without_pw_hash(fake_users_db, username=token_data.username)
            if user is None:
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
            token_data = TokenData(username=username)
            user = get_user_without_pw_hash(fake_users_db, username=token_data.username)
            if user is None:
                raise credentials_exception
            return user
        else:
            logger.info('token expired ')

    except jwt.exceptions.PyJWTError as e:
        logger.error(f'oidc user is considered as non oidc user: {e}')
        _jwt_error = e

    # try as oidc user
    headers = {'Authorization': 'bearer ' + token}
    r_user = requests.get(
        KEYCLOAK_BASEURL + '/userinfo',
        headers=headers,
        verify=False
    )
    if r_user.status_code == HTTP_200_OK:
        user = dict(r_user.json())
        # update user and roles in db
        update_oidc_user(db=SessionLocal(), oidc_user=OIDC_User_Create.parse_obj(user))
        # align to usual naming for usernames
        user['username'] = user['preferred_username']
        return user
    elif r_user.status_code == HTTP_401_UNAUTHORIZED:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail=r_user.json()
        )
    elif _jwt_error:
        raise credentials_exception
    else:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Internal authentication error (our bad)'
        )


async def get_current_active_user(
        current_user: Annotated[User, Depends(get_current_user)]):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


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
