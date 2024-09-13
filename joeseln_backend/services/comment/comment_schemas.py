import datetime
import json
from typing import List, Any
from pydantic import BaseModel, Field, Json
from uuid import UUID

from joeseln_backend.conf.content_types import *
from joeseln_backend.conf.mocks.mock_user import MockUser


class Comment(BaseModel):
    id: int | str | UUID = Field(..., alias='pk')

    content: str
    version_number: int

    created_at: datetime.datetime
    created_by_id: int
    created_by: Json[Any] = json.loads(MockUser)

    last_modified_at: datetime.datetime
    last_modified_by_id: int
    last_modified_by: Json[Any] = json.loads(MockUser)

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
