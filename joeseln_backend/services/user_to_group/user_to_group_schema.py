import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class Group_Create(BaseModel):
    groupname: str


class Group(BaseModel):
    id: int | str | UUID = Field(..., alias='pk')
    groupname: str
    created_at: datetime.datetime
    last_modified_at: datetime.datetime

    class Config:
        populate_by_name = True
        from_attributes = True


class ExtendedGroup(BaseModel):
    id: int | str | UUID = Field(..., alias='pk')
    groupname: str
    created_at: datetime.datetime
    last_modified_at: datetime.datetime
    group_empty: bool

    class Config:
        populate_by_name = True
        from_attributes = True


class UserToGroup_Create(BaseModel):
    user_id: int | str | UUID
    group_id: int | str | UUID
    user_group_role: int | str | UUID
    external: bool

    class Config:
        populate_by_name = True
        from_attributes = True
