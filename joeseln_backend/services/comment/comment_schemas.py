import datetime
from typing import List
from pydantic import BaseModel, Field
from uuid import UUID

from joeseln_backend.conf.content_types import comment_content_type, comment_content_type_model
from joeseln_backend.services.user.user_schema import User


class Comment(BaseModel):
    id: int | str | UUID = Field(..., alias='pk')

    content: str
    version_number: int

    created_at: datetime.datetime
    created_by_id: int
    created_by: User

    last_modified_at: datetime.datetime
    last_modified_by_id: int
    last_modified_by: User

    deleted: bool

    content_type: int = comment_content_type
    content_type_model: str = comment_content_type_model

    # mocked
    display: int | str | UUID = 'Left object id ?, right object id ?'
    is_favourite: bool = False
    my_metadata: List[str] = []
    url: str = ''

    class Config:
        populate_by_name = True
        from_attributes = True


class CreateComment(BaseModel):
    content: str
    private: bool
    relates_to_content_type_id: int
    relates_to_pk: int | str | UUID
