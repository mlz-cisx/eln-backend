import datetime
import json

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from joeseln_backend.conf.content_types import file_content_type_version
from joeseln_backend.models import models
from joeseln_backend.mylogging.root_logger import logger
from joeseln_backend.services.file import file_service
from joeseln_backend.services.labbook.labbook_service import check_for_labbook_access
from joeseln_backend.services.labbookchildelements.labbookchildelement_service import (
    check_for_version_edit_access_on_lb_elem,
)


def get_all_file_versions(db: Session, file_pk, user):
    db_file_versions = db.query(models.Version).filter_by(
        object_id=file_pk).order_by(models.Version.number.desc()).all()
    # renaming and json.dumps for schema
    for db_file_version in db_file_versions:
        db_file_version.metadata = json.dumps(
            json.loads(json.dumps(db_file_version.version_metadata)))
        db_user_created = db.query(models.User).get(
            db_file_version.created_by_id)
        db_user_modified = db.query(models.User).get(
            db_file_version.last_modified_by_id)
        db_file_version.created_by = db_user_created
        db_file_version.last_modified_by = db_user_modified

    db_file = db.query(models.File).get(file_pk)
    lb_elem = db.query(models.Labbookchildelement).get(db_file.elem_id)

    if lb_elem and check_for_labbook_access(
        db=db, labbook_pk=lb_elem.labbook_id, user=user
    ):
        return db_file_versions
    return None


def get_file_version_metadata(db: Session, file_pk, version_pk, user):
    db_file = db.query(models.File).get(file_pk)
    lb_elem = db.query(models.Labbookchildelement).get(db_file.elem_id)
    if lb_elem and check_for_labbook_access(db=db,
                                            labbook_pk=lb_elem.labbook_id,
                                            user=user) and check_for_version_edit_access_on_lb_elem(
        db=db, lb_elem=lb_elem, user=user):
        db_file_version = db.query(models.Version).get(version_pk)
        # renaming and json.dumps for schema
        return db_file_version.version_metadata
    return None


def restore_file_version(db: Session, file_pk, version_pk, user):
    db_file_version = db.query(models.Version).get(version_pk)
    summary = f'restored from v{db_file_version.number}'
    version_metadata = db_file_version.version_metadata
    description = version_metadata['description']
    title = version_metadata['title']
    db_file = add_file_version(db=db, file_pk=file_pk, summary=summary,
                               restored_description=description,
                               restored_title=title, user=user)[0]

    return db_file


def add_file_version(db: Session, file_pk, summary, user,
                     restored_description=None,
                     restored_title=None):
    db_file = db.query(models.File).get(file_pk)
    if db_file:
        lb_elem = db.query(models.Labbookchildelement).get(db_file.elem_id)
        if check_for_labbook_access(db=db, labbook_pk=lb_elem.labbook_id,
                                    user=user) and check_for_version_edit_access_on_lb_elem(
            db=db, lb_elem=lb_elem, user=user):

            number = 1
            last_db_file_version = db.query(models.Version).filter_by(
                object_id=file_pk).order_by(
                models.Version.number.desc()).first()
            if last_db_file_version:
                number = last_db_file_version.number + 1

            if restored_description or restored_title:
                db_file.description = restored_description
                db_file.title = restored_title
                try:
                    db.commit()
                except SQLAlchemyError as e:
                    logger.error(e)
                db.refresh(db_file)
                file_service.restore_file(db=db, file_pk=file_pk, user=user)

            version_metadata = {
                'name': db_file.name,
                'title': db_file.title,
                'description': db_file.description
            }

            db_file_version = models.Version(
                object_id=file_pk,
                version_metadata=version_metadata,
                number=number,
                summary=summary,
                display=summary,
                content_type_pk=file_content_type_version,
                created_at=datetime.datetime.now(),
                created_by_id=user.id,
                last_modified_at=datetime.datetime.now(),
                last_modified_by_id=user.id
            )

            db_user_created = db.query(models.User).get(db_file.created_by_id)
            db_user_modified = db.query(models.User).get(
                db_file.last_modified_by_id)
            db_file.created_by = db_user_created
            db_file.last_modified_by = db_user_modified

            db.add(db_file_version)
            db.commit()
            db.refresh(db_file_version)
            # first element for main and restore, second for labbook_version_service
            return [db_file, db_file_version]
        return [None, None]
    return [None, None]
