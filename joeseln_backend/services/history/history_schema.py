import datetime
from typing import List
from pydantic import BaseModel, Field
from uuid import UUID
from joeseln_backend.services.user.user_schema import User


class ChangeRecord(BaseModel):
    field_name: str | None
    old_value: str | None
    new_value: str | None


class HistoryObjectType(BaseModel):
    id: int
    app_label: str
    model: str


class ElemHistory(BaseModel):
    id: int | str | UUID = Field(..., alias='pk')
    user: User
    object_type: HistoryObjectType
    object_uuid: UUID
    changeset_type: str
    date: datetime.datetime
    change_records: List[ChangeRecord]

    class Config:
        populate_by_name = True
