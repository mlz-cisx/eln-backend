import datetime
from typing import Any, List
from uuid import UUID

from pydantic import BaseModel, Field, Json

from joeseln_backend.conf.content_types import (
    picture_content_type,
    picture_content_type_model,
    version_content_type,
    version_content_type_model,
)
from joeseln_backend.services.privileges.privileges_schema import Privileges
from joeseln_backend.services.user.user_schema import User


class Picture(BaseModel):
    # for details page
    id: int | str | UUID = Field(..., alias='pk')
    version_number: int
    created_at: datetime.datetime
    created_by_id: int
    last_modified_at: datetime.datetime
    last_modified_by_id: int
    deleted: bool
    # src path from uploaded_picture_entry_id with jwt token
    background_image: str = Field(..., alias='download_background_image')
    # src path from uploaded_picture_entry_id with jwt token
    rendered_image: str = Field(..., alias='download_rendered_image')
    # src path for shapes uploaded_picture_entry_id
    shapes_image: str = Field(..., alias='download_shapes')
    height: int
    width: int
    scale: float
    title: str

    content_type: int = picture_content_type
    content_type_model: str = picture_content_type_model
    last_modified_by: User
    created_by: User
    # alt
    display: str
    fake_metadata: List[str] = []
    is_favourite: bool = False
    projects: List[Any] = []

    class Config:
        populate_by_name = True
        from_attributes = True


class PictureVersionSummary(BaseModel):
    summary: str


class PictureVersion(BaseModel):
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


class PicturePreviewVersion(BaseModel):
    title: str
    metadata: List[Any]
    projects: List[Any]
    metadata_version: int

    uploaded_file_entry: int | str | UUID | None = 'foo'

    class Config:
        populate_by_name = True
        from_attributes = True


class PictureWithPrivileges(BaseModel):
    picture: Picture | None
    privileges: Privileges | None


class UpdatePictureTitle(BaseModel):
    title: str


class PictureWithLbTitle(Picture):
    lb_title: str | None
