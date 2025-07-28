import datetime
from typing import List, Any, Optional
from pydantic import BaseModel, Field, Json
from uuid import UUID

from joeseln_backend.conf.content_types import labbook_content_type, labbook_content_type_model, version_content_type, version_content_type_model
from joeseln_backend.services.privileges.privileges_schema import Privileges
from joeseln_backend.services.user.user_schema import User


class Labbook(BaseModel):
    id: int | str | UUID = Field(..., alias='pk')
    version_number: int
    deleted: bool
    title: str
    strict_mode: bool
    created_at: datetime.datetime
    created_by_id: int
    last_modified_at: datetime.datetime
    last_modified_by_id: int
    description: str

    display: str = ''
    my_metadata: List[str] = []
    content_type_model: str = labbook_content_type_model
    projects: List[str] = []
    url: str = ''
    last_modified_by: User
    created_by: User
    content_type: int = labbook_content_type
    is_favourite: bool = False

    class Config:
        populate_by_name = True


class LabbookWithLen(Labbook):
    length: int


class LabbookCreate(BaseModel):
    title: str
    description: str


class LabbookPatch(BaseModel):
    title: str | Optional[bool] = Field(None)
    strict_mode: bool | Optional[bool] = Field(None)
    projects: List[str] | Optional[bool] = Field(None)
    description: str | Optional[bool] = Field(None)

    class Config:
        populate_by_name = True
        from_attributes = True


class LabbookVersionSummary(BaseModel):
    summary: str


class LabbookVersion(BaseModel):
    id: int | str | UUID = Field(..., alias='pk')
    object_id: int | str | UUID
    metadata: Json[Any]
    number: int
    summary: str
    display: str
    content_type_pk: int
    created_at: datetime.datetime
    last_modified_at: datetime.datetime

    content_type_model: str = version_content_type_model
    content_type: int = version_content_type

    last_modified_by: User
    created_by: User

    class Config:
        populate_by_name = True
        from_attributes = True


class LabbookPreviewVersion(BaseModel):
    title: str
    description: str
    child_elements: List[Any]

    metadata: List[Any]
    projects: List[Any]
    metadata_version: int

    class Config:
        populate_by_name = True
        from_attributes = True


class LabbookWithPrivileges(BaseModel):
    labbook: Labbook | None
    privileges: Privileges | None
