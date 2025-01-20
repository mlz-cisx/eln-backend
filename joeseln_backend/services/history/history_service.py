from sqlalchemy import desc
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import datetime

from joeseln_backend.helper.debouncer import debounce

from joeseln_backend.conf.content_types import type2model
from joeseln_backend.models import models
from joeseln_backend.mylogging.root_logger import logger
from joeseln_backend.conf.base_conf import STATIC_HISTORY_DEBOUNCE


def create_history_entry(db: Session, elem_id, user, object_type_id,
                         changeset_type, changerecords):
    # changeset_types:
    # U : edited/updated, R : restored, S: trashed , I initialized/created
    db_changeset = models.ChangesetChangeset(
        date=datetime.datetime.now(),
        object_uuid=elem_id,
        object_type_id=object_type_id,
        user_id=user.id,
        object_id=0,
        changeset_type=changeset_type,
    )
    db.add(db_changeset)
    try:
        db.commit()
    except SQLAlchemyError as e:
        logger.error(e)
        db.close()
        return db_changeset
    db.refresh(db_changeset)

    # changerecord = [field_name,old_value,new_value]
    # changerecords = [changerecord, changerecord, .....]
    for changerecord in changerecords:
        db_changerecord = models.ChangesetChangerecord(
            field_name=changerecord[0],
            old_value=changerecord[1],
            new_value=changerecord[2],
            is_related=False,
            change_set_id=db_changeset.id
        )
        db.add(db_changerecord)
    try:
        db.commit()
    except SQLAlchemyError as e:
        logger.error(e)
        db.close()
        return

    return db_changeset


@debounce(wait_time=STATIC_HISTORY_DEBOUNCE)
def create_note_update_history_entry(db: Session, elem_id, user, object_type_id,
                                     changeset_type, changerecords):
    create_history_entry(db=db, elem_id=elem_id, user=user,
                         object_type_id=object_type_id,
                         changeset_type=changeset_type,
                         changerecords=changerecords)

@debounce(wait_time=STATIC_HISTORY_DEBOUNCE)
def create_file_update_history_entry(db: Session, elem_id, user, object_type_id,
                                changeset_type, changerecords):
    create_history_entry(db=db, elem_id=elem_id, user=user,
                         object_type_id=object_type_id,
                         changeset_type=changeset_type,
                         changerecords=changerecords)


def get_history(db: Session, elem_id, user):
    history_elems = db.query(models.ChangesetChangeset).filter_by(
        object_uuid=elem_id).order_by(
        desc(models.ChangesetChangeset.date)).all()
    for elem in history_elems:
        elem.user = db.query(models.User).get(elem.user_id)

        elem.object_type = {'id': elem.object_type_id,
                            'app_label':
                                type2model[elem.object_type_id].split('.')[0],
                            'model': type2model[elem.object_type_id].split('.')[
                                1]}
    return history_elems
