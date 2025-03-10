import datetime
from pydantic import BaseModel, Field
from uuid import UUID
from typing import Any

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
    username: str
    email: str
    first_name: str
    last_name: str
    password: str
    password_confirmed: str


class GuiUserPatch(BaseModel):
    username: str
    user_email: str
    first_name: str
    last_name: str


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
    password: str


class PasswordPatch(BaseModel):
    password_patch: str


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
