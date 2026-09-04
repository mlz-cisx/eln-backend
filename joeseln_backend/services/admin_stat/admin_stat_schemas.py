from pydantic import BaseModel


class StatResponse(BaseModel):
    total_users: int
    active_users: int
    total_labbook: int
    total_notes: int
    total_files: int
    total_pics: int
    image_folder_size: int
    files_folder_size: int
    git_commit_hash: str | None = None
    git_commit_msg: str | None = None
