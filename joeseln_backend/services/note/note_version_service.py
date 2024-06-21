from sqlalchemy.orm import Session
import json
from sqlalchemy.exc import SQLAlchemyError

from joeseln_backend.models import models
from joeseln_backend.services.note import note_service
from joeseln_backend.services.note.note_schemas import *
from joeseln_backend.conf.mocks.mock_user import FAKE_USER_ID



def get_all_note_versions(db: Session, note_pk):
    db_note_versions = db.query(models.Version).filter_by(
        object_id=note_pk).order_by(models.Version.number.desc()).all()
    # renaming and json.dumps for schema
    for db_note_version in db_note_versions:
        db_note_version.metadata = json.dumps(
            json.loads(json.dumps(db_note_version.version_metadata)))
    return db_note_versions


def get_note_version_metadata(db: Session, version_pk):
    db_note_version = db.query(models.Version).get(version_pk)
    # renaming and json.dumps for schema
    return db_note_version.version_metadata


def restore_note_version(db: Session, note_pk, version_pk):
    db_note_version = db.query(models.Version).get(version_pk)
    summary = f'restored from v{db_note_version.number}'
    version_metadata = db_note_version.version_metadata
    content = version_metadata['content']
    subject = version_metadata['subject']
    db_note = add_note_version(db=db, note_pk=note_pk, summary=summary,
                               restored_content=content,
                               restored_subject=subject)[0]

    return db_note


def add_note_version(db: Session, note_pk, summary, restored_content=None,
                     restored_subject=None):
    db_note = db.query(models.Note).get(note_pk)
    number = 1
    last_db_note_version = db.query(models.Version).filter_by(
        object_id=note_pk).order_by(models.Version.number.desc()).first()
    if last_db_note_version:
        number = last_db_note_version.number + 1

    if restored_subject or restored_content:
        db_note.subject = restored_subject
        db_note.content = restored_content
        try:
            db.commit()
        except SQLAlchemyError as e:
            print(e)
        db.refresh(db_note)
        note_service.restore_note(db=db, note_pk=note_pk)

    version_metadata = {
        'content': db_note.content,
        'subject': db_note.subject,
        'metadata': [],
        'projects': [],
        'metadata_version': 1
    }

    db_note_version = models.Version(
        object_id=note_pk,
        version_metadata=version_metadata,
        number=number,
        summary=summary,
        display=summary,
        content_type_pk=note_content_type_version,
        created_at=datetime.datetime.now(),
        created_by_id=FAKE_USER_ID,
        last_modified_at=datetime.datetime.now(),
        last_modified_by_id=FAKE_USER_ID
    )

    db.add(db_note_version)
    db.commit()
    db.refresh(db_note_version)
    # first element for main and restore, second for labbook_version_service
    return [db_note, db_note_version]

