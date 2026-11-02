import datetime
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, Field

from joeseln_backend.conf.base_conf import AUTH_CRED_LIMIT
from joeseln_backend.services.privileges.privileges_schema import Privileges


class User(BaseModel):
    id: int | str | UUID = Field(..., alias='pk')
    username: str
    email: str
    first_name: str | None = None
    last_name: str | None = None
    admin: bool | None = None
    groups: Any | None = None
    admin_groups: Any | None = None
    oidc_user: bool | None = None

    class Config:
        populate_by_name = True
        from_attributes = True


class UserExtended(BaseModel):
    id: int | str | UUID
    username: str
    email: str
    oidc_user: bool
    first_name: str
    last_name: str
    deleted: bool
    created_at: datetime.datetime
    last_modified_at: datetime.datetime

    class Config:
        populate_by_name = True
        from_attributes = True


class UserExtendedConnected(UserExtended):
    connected: bool


class UserExtendedWithGroups(UserExtended):
    groups: Any | None = None
    admin_groups: Any | None = None

    class Config:
        populate_by_name = True
        from_attributes = True


class AdminExtended(BaseModel):
    id: int | str | UUID
    username: str
    email: str
    oidc_user: bool
    first_name: str
    last_name: str
    admin: bool
    created_at: datetime.datetime
    last_modified_at: datetime.datetime

    class Config:
        populate_by_name = True
        from_attributes = True


class UserCreate(BaseModel):
    username: str
    email: str
    oidc_user: bool
    password: str
    first_name: str
    last_name: str


class GuiUserCreate(BaseModel):
    username: Annotated[str, Field(max_length=AUTH_CRED_LIMIT)]
    email: Annotated[str, Field(max_length=AUTH_CRED_LIMIT)]
    first_name: Annotated[str, Field(max_length=AUTH_CRED_LIMIT)]
    last_name: Annotated[str, Field(max_length=AUTH_CRED_LIMIT)]
    password: Annotated[str, Field(max_length=AUTH_CRED_LIMIT)]
    password_confirmed: Annotated[str, Field(max_length=AUTH_CRED_LIMIT)]


class GuiUserPatch(BaseModel):
    username: Annotated[str, Field(max_length=AUTH_CRED_LIMIT)]
    user_email: Annotated[str, Field(max_length=AUTH_CRED_LIMIT)]
    first_name: Annotated[str, Field(max_length=AUTH_CRED_LIMIT)]
    last_name: Annotated[str, Field(max_length=AUTH_CRED_LIMIT)]


class OIDCUserCreate(BaseModel):
    preferred_username: str
    email: str
    given_name: str
    family_name: str
    realm_access: Any | None = None

    class Config:
        populate_by_name = True
        from_attributes = True


class PasswordChange(BaseModel):
    password: Annotated[str, Field(max_length=AUTH_CRED_LIMIT)]
    old_password: Annotated[str, Field(max_length=AUTH_CRED_LIMIT)] = Field(
        ..., min_length=1
    )


class PasswordPatch(BaseModel):
    password_patch: Annotated[str, Field(max_length=AUTH_CRED_LIMIT)]
    old_password: Annotated[str, Field(max_length=AUTH_CRED_LIMIT)] | None = None


class UserWithPrivileges(BaseModel):
    user: UserExtendedWithGroups | None
    privileges: Privileges | None


class GroupUserExtended(BaseModel):
    id: int | str | UUID
    username: str
    email: str
    oidc_user: bool
    first_name: str
    last_name: str
    deleted: bool
    in_group: bool
    created_at: datetime.datetime
    last_modified_at: datetime.datetime

    class Config:
        populate_by_name = True
        from_attributes = True
