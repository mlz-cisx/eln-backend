from sqlalchemy.orm import Session
import json
from sqlalchemy.exc import SQLAlchemyError

from joeseln_backend.services.labbook.labbook_service import \
    check_for_labbook_access
from joeseln_backend.services.labbookchildelements.labbookchildelement_service import \
    check_for_version_edit_access_on_lb_elem
from joeseln_backend.services.picture import picture_service
from joeseln_backend.models import models
from joeseln_backend.services.note.note_schemas import *

from joeseln_backend.mylogging.root_logger import logger


def get_all_picture_versions(db: Session, picture_pk, user):
    db_picture_versions = db.query(models.Version).filter_by(
        object_id=picture_pk).order_by(models.Version.number.desc()).all()
    # renaming and json.dumps for schema
    for db_picture_version in db_picture_versions:
        db_picture_version.metadata = json.dumps(
            json.loads(json.dumps(db_picture_version.version_metadata)))
        db_user_created = db.query(models.User).get(
            db_picture_version.created_by_id)
        db_user_modified = db.query(models.User).get(
            db_picture_version.last_modified_by_id)
        db_picture_version.created_by = db_user_created
        db_picture_version.last_modified_by = db_user_modified

    db_pic = db.query(models.Picture).get(picture_pk)
    lb_elem = db.query(models.Labbookchildelement).get(db_pic.elem_id)
    #
    if lb_elem and check_for_labbook_access(db=db,
                                            labbook_pk=lb_elem.labbook_id,
                                            user=user) and check_for_version_edit_access_on_lb_elem(
        db=db, lb_elem=lb_elem, user=user):
        return db_picture_versions
    return None


def get_picture_version_metadata(db: Session, picture_pk, version_pk, user):
    db_pic = db.query(models.Picture).get(picture_pk)
    lb_elem = db.query(models.Labbookchildelement).get(db_pic.elem_id)
    if lb_elem and check_for_labbook_access(db=db,
                                            labbook_pk=lb_elem.labbook_id,
                                            user=user) and check_for_version_edit_access_on_lb_elem(
        db=db, lb_elem=lb_elem, user=user):
        db_picture_version = db.query(models.Version).get(version_pk)
        # renaming and json.dumps for schema
        return db_picture_version.version_metadata
    return None


def restore_picture_version(db: Session, picture_pk, version_pk, user):
    db_picture_version = db.query(models.Version).get(version_pk)
    summary = f'restored from v{db_picture_version.number}'
    version_metadata = db_picture_version.version_metadata
    title = version_metadata['title']
    ri_img = version_metadata['ri_img']
    shapes = version_metadata['shapes']
    # user authorization is done in add picture version
    db_picture = add_picture_version(db=db, picture_pk=picture_pk,
                                     summary=summary,
                                     restored_title=title,
                                     restored_ri_img=ri_img,
                                     restored_shapes=shapes,
                                     user=user)[0]

    return db_picture


def add_picture_version(db: Session, picture_pk, summary, user,
                        restored_title=None,
                        restored_ri_img=None,
                        restored_shapes=None):
    pic_to_test = db.query(models.Picture).get(picture_pk)
    if pic_to_test:
        lb_elem = db.query(models.Labbookchildelement).get(pic_to_test.elem_id)
        if check_for_labbook_access(db=db, labbook_pk=lb_elem.labbook_id,
                                    user=user) and check_for_version_edit_access_on_lb_elem(
            db=db, lb_elem=lb_elem, user=user):

            if restored_title is None:
                paths = picture_service.copy_and_update_picture(db=db,
                                                                picture_pk=picture_pk)
                restored_ri_img = paths[0]
                restored_shapes = paths[1]

            else:
                paths = picture_service.copy_and_update_picture(db=db,
                                                                picture_pk=picture_pk,
                                                                restored_ri=restored_ri_img,
                                                                restored_shapes=restored_shapes)
                restored_ri_img = paths[0]
                restored_shapes = paths[1]

            number = 1
            last_db_picture_version = db.query(models.Version).filter_by(
                object_id=picture_pk).order_by(
                models.Version.number.desc()).first()
            if last_db_picture_version:
                number = last_db_picture_version.number + 1

            # has new path
            db_picture = db.query(models.Picture).get(picture_pk)
            db_user_created = db.query(models.User).get(
                db_picture.created_by_id)
            db_user_modified = db.query(models.User).get(
                db_picture.last_modified_by_id)
            db_picture.created_by = db_user_created
            db_picture.last_modified_by = db_user_modified

            if restored_title is not None:
                db_picture.title = restored_title
                try:
                    db.commit()
                except SQLAlchemyError as e:
                    logger.error(e)
                db.refresh(db_picture)
                picture_service.restore_picture(db=db, picture_pk=picture_pk,
                                                user=user)

            version_metadata = {
                'title': db_picture.title,
                'scale': db_picture.scale,
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
                created_by_id=user.id,
                last_modified_at=datetime.datetime.now(),
                last_modified_by_id=user.id
            )

            db.add(db_picture_version)
            db.commit()
            db.refresh(db_picture_version)
            # first element for main and restore, second for labbook_version_service
            return [db_picture, db_picture_version]
        return [None, None]
    return [None, None]
