from sqlalchemy.orm import Session
from joeseln_backend.models import models


def create_path(db: Session):
    path = models.FilePath()
    db.add(path)
    db.commit()
    db.refresh(path)
    return path.id


def create_entry(db: Session):
    entry = models.UploadEntry()
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry.id
