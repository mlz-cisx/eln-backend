import datetime
from pydantic import BaseModel, Field
from uuid import UUID
from typing import Any


class User(BaseModel):
    id: int | str | UUID | None = None
    username: str
    email: str
    first_name: str | None = None
    last_name: str | None = None
    groups: Any | None = None

    class Config:
        populate_by_name = True
        from_attributes = True


class UserExtended(BaseModel):
    id: int | str | UUID = Field(..., alias='pk')
    username: str
    email: str
    oidc_user: bool
    password: str
    first_name: str
    last_name: str
    created_at: datetime.datetime
    last_modified_at: datetime.datetime

    class Config:
        populate_by_name = True
        from_attributes = True


class User_Create(BaseModel):
    username: str
    email: str
    oidc_user: bool
    password: str
    first_name: str
    last_name: str


class OIDC_User_Create(BaseModel):
    preferred_username: str
    email: str
    given_name: str
    family_name: str
    realm_access: Any | None = None

    class Config:
        populate_by_name = True
        from_attributes = True
