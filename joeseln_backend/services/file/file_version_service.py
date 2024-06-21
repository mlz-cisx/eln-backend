from sqlalchemy.orm import Session
import json
from sqlalchemy.exc import SQLAlchemyError

from joeseln_backend.models import models
from joeseln_backend.services.file import file_service
from joeseln_backend.services.file.file_schemas import *
from joeseln_backend.conf.mocks.mock_user import FAKE_USER_ID





def get_all_file_versions(db: Session, file_pk):
    db_file_versions = db.query(models.Version).filter_by(
        object_id=file_pk).order_by(models.Version.number.desc()).all()
    # renaming and json.dumps for schema
    for db_file_version in db_file_versions:
        db_file_version.metadata = json.dumps(
            json.loads(json.dumps(db_file_version.version_metadata)))
    return db_file_versions


def get_file_version_metadata(db: Session, version_pk):
    db_file_version = db.query(models.Version).get(version_pk)
    # renaming and json.dumps for schema
    return db_file_version.version_metadata


def restore_file_version(db: Session, file_pk, version_pk):
    db_file_version = db.query(models.Version).get(version_pk)
    summary = f'restored from v{db_file_version.number}'
    version_metadata = db_file_version.version_metadata
    description = version_metadata['description']
    title = version_metadata['title']
    db_file = add_file_version(db=db, file_pk=file_pk, summary=summary,
                               restored_description=description,
                               restored_title=title)[0]

    return db_file


def add_file_version(db: Session, file_pk, summary, restored_description=None,
                     restored_title=None):
    db_file = db.query(models.File).get(file_pk)
    number = 1
    last_db_file_version = db.query(models.Version).filter_by(
        object_id=file_pk).order_by(models.Version.number.desc()).first()
    if last_db_file_version:
        number = last_db_file_version.number + 1

    if restored_description or restored_title:
        db_file.description = restored_description
        db_file.title = restored_title
        try:
            db.commit()
        except SQLAlchemyError as e:
            print(e)
        db.refresh(db_file)
        file_service.restore_file(db=db, file_pk=file_pk)


    version_metadata = {
        'name': db_file.name,
        'title': db_file.title,
        'description': db_file.description,
        'metadata': [],
        'projects': [],
        'metadata_version': 1
    }

    db_file_version = models.Version(
        object_id=file_pk,
        version_metadata=version_metadata,
        number=number,
        summary=summary,
        display=summary,
        content_type_pk=file_content_type_version,
        created_at=datetime.datetime.now(),
        created_by_id=FAKE_USER_ID,
        last_modified_at=datetime.datetime.now(),
        last_modified_by_id=FAKE_USER_ID
    )

    db.add(db_file_version)
    db.commit()
    db.refresh(db_file_version)
    # first element for main and restore, second for labbook_version_service
    return [db_file,db_file_version]
