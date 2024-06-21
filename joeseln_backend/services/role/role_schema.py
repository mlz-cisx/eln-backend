import datetime
from pydantic import BaseModel, Field
from uuid import UUID


class Role(BaseModel):
    id: int | str | UUID = Field(..., alias='pk')
    rolename: str
    description: str
    created_at: datetime.datetime
    last_modified_at: datetime.datetime

    class Config:
        populate_by_name = True
        from_attributes = True


class Role_Create(BaseModel):
    rolename: str
    description: str
