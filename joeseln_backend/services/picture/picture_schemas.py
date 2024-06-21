import datetime
from typing import List, Any
from pydantic import BaseModel, Field, Json
from uuid import UUID

from joeseln_backend.conf.content_types import *
from joeseln_backend.conf.mocks.mock_user import MockUser


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
    title : str

    content_type: int = picture_content_type
    content_type_model: str = picture_content_type_model
    last_modified_by: Json[Any] = MockUser
    created_by: Json[Any] = MockUser
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

    created_by: Json[Any] = MockUser
    last_modified_by: Json[Any] = MockUser

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