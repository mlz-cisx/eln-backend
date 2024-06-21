from sqlalchemy.orm import Session
import json
from sqlalchemy.exc import SQLAlchemyError

from joeseln_backend.services.picture import picture_service
from joeseln_backend.models import models
from joeseln_backend.services.note.note_schemas import *
from joeseln_backend.conf.mocks.mock_user import FAKE_USER_ID


def get_all_picture_versions(db: Session, picture_pk):
    db_picture_versions = db.query(models.Version).filter_by(
        object_id=picture_pk).order_by(models.Version.number.desc()).all()
    # renaming and json.dumps for schema
    for db_picture_version in db_picture_versions:
        db_picture_version.metadata = json.dumps(
            json.loads(json.dumps(db_picture_version.version_metadata)))
    return db_picture_versions


def get_picture_version_metadata(db: Session, version_pk):
    db_picture_version = db.query(models.Version).get(version_pk)
    # renaming and json.dumps for schema
    return db_picture_version.version_metadata


def restore_picture_version(db: Session, picture_pk, version_pk):
    db_picture_version = db.query(models.Version).get(version_pk)
    summary = f'restored from v{db_picture_version.number}'
    version_metadata = db_picture_version.version_metadata
    title = version_metadata['title']
    ri_img = version_metadata['ri_img']
    shapes = version_metadata['shapes']
    db_picture = add_picture_version(db=db, picture_pk=picture_pk,
                                     summary=summary,
                                     restored_title=title,
                                     restored_ri_img=ri_img,
                                     restored_shapes=shapes)[0]

    return db_picture


def add_picture_version(db: Session, picture_pk, summary,
                        restored_title=None, restored_ri_img=None,
                        restored_shapes=None):
    if restored_title is None:
        paths = picture_service.copy_and_update_picture(db=db,
                                                        picture_pk=picture_pk)
        restored_ri_img = paths[0]
        restored_shapes = paths[1]

    number = 1
    last_db_picture_version = db.query(models.Version).filter_by(
        object_id=picture_pk).order_by(models.Version.number.desc()).first()
    if last_db_picture_version:
        number = last_db_picture_version.number + 1

    # has new path
    db_picture = db.query(models.Picture).get(picture_pk)

    if restored_title is not None:
        db_picture.title = restored_title
        db_picture.rendered_image = restored_ri_img
        db_picture.shapes_image = restored_shapes
        try:
            db.commit()
        except SQLAlchemyError as e:
            print(e)
        db.refresh(db_picture)
        picture_service.restore_picture(db=db, picture_pk=picture_pk)

    version_metadata = {
        'title': db_picture.title,
        'ri_img': restored_ri_img,
        'shapes': restored_shapes,
        'metadata': [],
        'projects': [],
        'metadata_version': 1
    }

    db_picture_version = models.Version(
        object_id=picture_pk,
        version_metadata=version_metadata,
        number=number,
        summary=summary,
        display=summary,
        content_type_pk=picture_content_type_version,
        created_at=datetime.datetime.now(),
        created_by_id=FAKE_USER_ID,
        last_modified_at=datetime.datetime.now(),
        last_modified_by_id=FAKE_USER_ID
    )

    db.add(db_picture_version)
    db.commit()
    db.refresh(db_picture_version)
    # first element for main and restore, second for labbook_version_service
    return [db_picture, db_picture_version]
