from pydantic import BaseModel


class Privileges(BaseModel):
    fullAccess: bool
    view: bool
    edit: bool
    delete: bool
    trash: bool
    restore: bool

    class Config:
        populate_by_name = True
        from_attributes = True