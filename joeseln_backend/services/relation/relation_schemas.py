import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from joeseln_backend.conf.content_types import relation_content_type
from joeseln_backend.services.comment.comment_schemas import Comment
from joeseln_backend.services.file.file_schemas import File
from joeseln_backend.services.note.note_schemas import Note
from joeseln_backend.services.picture.picture_schemas import Picture
from joeseln_backend.services.user.user_schema import User


class Relation(BaseModel):
    id: int | str | UUID = Field(..., alias='pk')

    content_type: int = relation_content_type
    content_type_model: str = 'relations.relation'

    left_content_object: Picture | Note | File | Comment | None
    left_content_type: int
    left_content_type_model: str
    left_object_id: int | str | UUID

    private: bool
    deleted: bool

    right_content_object: Picture | Note | File | Comment | None
    right_content_type: int
    right_content_type_model: str
    right_object_id: int | str | UUID

    created_at: datetime.datetime
    created_by_id: int

    last_modified_at: datetime.datetime
    last_modified_by_id: int

    last_modified_by: User
    created_by: User

    display: str = 'Left object id ?, right object id ?'

    class Config:
        populate_by_name = True
        from_attributes = True
