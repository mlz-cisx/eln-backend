import datetime
from typing import List, Any
from pydantic import BaseModel, Field, Json
from uuid import UUID

from joeseln_backend.conf.content_types import *
from joeseln_backend.conf.mocks.mock_user import MockUser
from joeseln_backend.services.privileges.privileges_schema import Privileges


class Labbook(BaseModel):
    id: int | str | UUID = Field(..., alias='pk')
    version_number: int
    deleted: bool
    title: str
    created_at: datetime.datetime
    created_by_id: int
    last_modified_at: datetime.datetime
    last_modified_by_id: int
    description: str

    display: str = ''
    my_metadata: List[str] = []
    content_type_model: str = labbook_content_type_model
    is_template: bool = False
    projects: List[str] = []
    url: str = ''
    created_by: List[str] = []
    last_modified_by: List[str] = []
    content_type: int = labbook_content_type
    is_favourite: bool = False

    class Config:
        populate_by_name = True


class LabbookCreate(BaseModel):
    title: str
    description: str


class LabbookPatch(BaseModel):
    title: str
    is_template: bool
    projects: List[str]

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

    created_by: Json[Any] = MockUser
    last_modified_by: Json[Any] = MockUser

    class Config:
        populate_by_name = True
        from_attributes = True


class LabbookPreviewVersion(BaseModel):
    title: str
    description: str
    is_template : bool
    child_elements : List[Any]

    metadata: List[Any]
    projects: List[Any]
    metadata_version: int


    class Config:
        populate_by_name = True
        from_attributes = True


class labbook_with_privileges(BaseModel):
    labbook: Labbook | None
    privileges: Privileges | None
