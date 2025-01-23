import datetime
from typing import List, Any
from pydantic import BaseModel, Field, Json
from uuid import UUID

from joeseln_backend.conf.content_types import *
from joeseln_backend.services.privileges.privileges_schema import Privileges
from joeseln_backend.services.user.user_schema import User


class File(BaseModel):
    id: int | str | UUID = Field(..., alias='pk')
    version_number: int
    created_at: datetime.datetime
    created_by_id: int
    last_modified_at: datetime.datetime
    last_modified_by_id: int
    deleted: bool
    imported: bool
    # the display , display, original_filename are the same
    name: str
    display: str
    original_filename: str
    # title from description
    title: str
    # editor content
    description: str
    file_size: int
    # download url we overwrite path
    path: str = Field(..., alias='download')

    container_id: str | None = None
    envelope_id: str | None = None
    mime_type: str | None
    # we don't need this
    directory_id: str = 'foo'
    location: str = ''
    content_type: int = file_content_type
    content_type_model: str = file_content_type_model
    last_modified_by: User
    created_by: User
    fake_metadata: List[str] = []
    is_favourite: bool = False
    is_dss_file: bool = False
    projects: List[Any] = []
    url: str = ''

    class Config:
        populate_by_name = True
        from_attributes = True


class FilePatch(BaseModel):
    title: str
    description: str


class FileVersionSummary(BaseModel):
    summary: str


class FileVersion(BaseModel):
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

    created_by: User
    last_modified_by: User

    class Config:
        populate_by_name = True
        from_attributes = True


class FilePreviewVersion(BaseModel):
    name: str
    title: str
    description: str
    metadata: List[Any]
    projects: List[Any]
    metadata_version: int

    directory: None = None
    uploaded_file_entry: int | str | UUID | None = 'foo'

    class Config:
        populate_by_name = True
        from_attributes = True


class FileWithPrivileges(BaseModel):
    file: File | None
    privileges: Privileges | None


class FileWithLbTitle(File):
    lb_title: str | None
