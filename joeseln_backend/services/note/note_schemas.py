import datetime
from typing import List, Any
from pydantic import BaseModel, Field, Json
from uuid import UUID

from joeseln_backend.conf.content_types import *
from joeseln_backend.conf.mocks.mock_user import MockUser
from joeseln_backend.services.privileges.privileges_schema import Privileges
from joeseln_backend.services.user.user_schema import User


class Note(BaseModel):
    id: int | str | UUID = Field(..., alias='pk')
    subject: str
    content: str
    version_number: int
    created_at: datetime.datetime
    created_by_id: int
    last_modified_at: datetime.datetime
    last_modified_by_id: int
    deleted: bool

    content_type: int = note_content_type
    content_type_model: str = note_content_type_model
    last_modified_by: User | Json[Any] = MockUser
    created_by: User | Json[Any] = MockUser
    display: str = ''
    fake_metadata: List[str] = []
    is_favourite: bool = False
    projects: List[Any] = []

    class Config:
        populate_by_name = True
        from_attributes = True


class NoteCreate(BaseModel):
    subject: str
    content: str


class NoteVersionSummary(BaseModel):
    summary: str


class NoteVersion(BaseModel):
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

    last_modified_by: User | Json[Any] = MockUser
    created_by: User | Json[Any] = MockUser

    class Config:
        populate_by_name = True
        from_attributes = True


class NotePreviewVersion(BaseModel):
    content: str
    subject: str
    metadata: List[Any]
    projects: List[Any]
    metadata_version: int


class NoteWithPrivileges(BaseModel):
    note: Note | None
    privileges: Privileges | None
