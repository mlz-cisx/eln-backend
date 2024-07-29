import datetime
from pydantic import BaseModel, Field
from uuid import UUID


class Group_Create(BaseModel):
    groupname: str

class GetGroup(BaseModel):
    id: int | str | UUID = Field(..., alias='pk')
    groupname: str
    created_at: datetime.datetime
    last_modified_at: datetime.datetime

    class Config:
        populate_by_name = True
        from_attributes = True


class UserToGroup_Create(BaseModel):
    user_id: int | str | UUID
    group_id: int | str | UUID
    user_group_role: int | str | UUID

    class Config:
        populate_by_name = True
        from_attributes = True

class Privileges(BaseModel):
    fullAccess: bool
    view: bool
    edit: bool
    delete: bool
    trash: bool
    restore: bool
