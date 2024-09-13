import datetime

from pydantic import BaseModel, Field
from uuid import UUID

from joeseln_backend.conf.content_types import *
from joeseln_backend.services.note.note_schemas import Note
from joeseln_backend.services.picture.picture_schemas import Picture
from joeseln_backend.services.file.file_schemas import File


class Labbookchildelement(BaseModel):
    id: int | str | UUID = Field(..., alias='pk')
    labbook_id: int | str | UUID

    position_x: int
    position_y: int
    width: int
    height: int

    child_object_id: int | str | UUID
    child_object_content_type: int
    child_object_content_type_model: str
    version_number: int
    child_object: Picture | Note | File | None

    created_at: datetime.datetime
    created_by_id: int
    last_modified_at: datetime.datetime
    last_modified_by_id: int

    # mocked fields
    num_related_comments: int
    num_relations: int = 0
    content_type: int = element_content_type

    class Config:
        populate_by_name = True
        from_attributes = True


class Labbookchildelement_Create(BaseModel):
    position_x: int
    position_y: int
    width: int
    height: int
    child_object_id: int | str | UUID
    child_object_content_type: int


class Labbookchildelement_Update(BaseModel):
    position_x: int
    position_y: int
    width: int
    height: int
    id: int | str | UUID = Field(..., alias='pk')

    class Config:
        populate_by_name = True
        from_attributes = True


class Labbookchildelement_Delete(BaseModel):
    labbook_pk: int | str | UUID
