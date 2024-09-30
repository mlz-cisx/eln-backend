from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import text

from joeseln_backend.auth import security
from joeseln_backend.ws.ws_client import transmit
from joeseln_backend.models import models
from joeseln_backend.services.note.note_schemas import *
from joeseln_backend.helper import db_ordering
from joeseln_backend.conf.mocks.mock_user import FAKE_USER_ID
from joeseln_backend.conf.base_conf import URL_BASE_PATH

from joeseln_backend.mylogging.root_logger import logger
from joeseln_backend.services.comment.comment_schemas import Comment


def get_all_notes(db: Session, params):
    order_params = db_ordering.get_order_params(ordering=params.get('ordering'))
    return db.query(models.Note).filter_by(
        deleted=bool(params.get('deleted'))).order_by(
        text(order_params)).offset(params.get('offset')).limit(
        params.get('limit')).all()


def get_note(db: Session, note_pk):
    db_note = db.query(models.Note).get(note_pk)
    db_user = db.query(models.User).get(db_note.created_by_id)
    db_note.created_by = db_user.username
    return db_note


def get_note_relations(db: Session, note_pk, params):
    if not params:
        relations = db.query(models.Relation).filter_by(
            right_object_id=note_pk, deleted=False).order_by(
            models.Relation.created_at).all()
    else:
        order_params = db_ordering.get_order_params(
            ordering=params.get('ordering'))

        relations = db.query(models.Relation).filter_by(
            right_object_id=note_pk, deleted=False).order_by(
            text(order_params)).offset(params.get('offset')).limit(
            params.get('limit')).all()

    for rel in relations:
        if rel.left_content_type == 70:
            rel.left_content_object = Comment.parse_obj(
                db.query(models.Comment).get(rel.left_object_id))
        else:
            rel.left_content_object = None
        rel.right_content_object = db.query(models.Note).get(note_pk)
    return relations


def delete_note_relation(db: Session, note_pk, relation_pk):
    db_relation = db.query(models.Relation).get(relation_pk)
    db_relation.deleted = True
    try:
        db.commit()
    except SQLAlchemyError as e:
        logger.error(e)
        db.close()
        return
    db.refresh(db_relation)

    return get_note_relations(db=db, note_pk=note_pk, params='')


def get_note_related_comments_count(db: Session, note_pk):
    relations_count = db.query(models.Relation).filter_by(
        right_object_id=note_pk, deleted=False, left_content_type=70).count()

    return relations_count


def create_note(db: Session, note: NoteCreate, user):
    db_note = models.Note(version_number=0,
                          subject=note.subject,
                          content=note.content,
                          created_at=datetime.datetime.now(),
                          created_by_id=user.id,
                          last_modified_at=datetime.datetime.now(),
                          last_modified_by_id=user.id)

    db.add(db_note)
    try:
        db.commit()
    except SQLAlchemyError as e:
        logger.error(e)
        db.close()
        return db_note
    db.refresh(db_note)
    db.close()
    db_note.last_modified_by = user
    db_note.created_by = user

    return db_note


def update_note(db: Session, note_pk, note: NoteCreate):
    note_to_update = db.query(models.Note).get(note_pk)
    note_to_update.subject = note.subject
    note_to_update.content = note.content
    note_to_update.last_modified_at = datetime.datetime.now()
    note_to_update.last_modified_by_id = FAKE_USER_ID

    lb_elem = db.query(models.Labbookchildelement).get(note_to_update.elem_id)
    lb_elem.last_modified_at = datetime.datetime.now()
    lb_elem.last_modified_by_id = FAKE_USER_ID

    lb_to_update = db.query(models.Labbook).get(lb_elem.labbook_id)
    lb_to_update.last_modified_at = datetime.datetime.now()
    lb_to_update.last_modified_by_id = FAKE_USER_ID
    try:
        db.commit()
    except SQLAlchemyError as e:
        logger.error(e)
        db.close()
        return note_to_update
    db.refresh(note_to_update)
    return note_to_update


def soft_delete_note(db: Session, note_pk, labbook_data):
    note_to_update = db.query(models.Note).get(note_pk)
    note_to_update.deleted = True
    note_to_update.last_modified_at = datetime.datetime.now()
    note_to_update.last_modified_by_id = FAKE_USER_ID

    lb_elem = db.query(models.Labbookchildelement).get(note_to_update.elem_id)
    lb_elem.deleted = True
    lb_elem.last_modified_at = datetime.datetime.now()
    lb_elem.last_modified_by_id = FAKE_USER_ID

    lb_to_update = db.query(models.Labbook).get(lb_elem.labbook_id)
    lb_to_update.last_modified_at = datetime.datetime.now()
    lb_to_update.last_modified_by_id = FAKE_USER_ID
    try:
        db.commit()
    except SQLAlchemyError as e:
        logger.error(e)
        db.close()
        return note_to_update
    db.refresh(note_to_update)
    query = db.query(models.Labbookchildelement).filter_by(
        labbook_id=labbook_data.labbook_pk, deleted=False).all()

    if not query:
        try:
            transmit(
                {'model_name': 'labbook', 'model_pk': labbook_data.labbook_pk})
        except RuntimeError as e:
            logger.error(e)
    return note_to_update


def restore_note(db: Session, note_pk):
    note_to_update = db.query(models.Note).get(note_pk)
    note_to_update.deleted = False
    note_to_update.last_modified_at = datetime.datetime.now()
    note_to_update.last_modified_by_id = FAKE_USER_ID

    lb_elem = db.query(models.Labbookchildelement).get(note_to_update.elem_id)
    lb_elem.deleted = False
    lb_elem.last_modified_at = datetime.datetime.now()
    lb_elem.last_modified_by_id = FAKE_USER_ID

    lb_to_update = db.query(models.Labbook).get(lb_elem.labbook_id)
    lb_to_update.last_modified_at = datetime.datetime.now()
    lb_to_update.last_modified_by_id = FAKE_USER_ID
    try:
        db.commit()
    except SQLAlchemyError as e:
        logger.error(e)
        db.close()
        return note_to_update
    db.refresh(note_to_update)
    return note_to_update


def get_note_export_link(db: Session, note_pk):
    db_note = db.query(models.Note).get(note_pk)
    db_note = build_note_download_url_with_token(note_to_process=db_note,
                                                 user='foo')
    export_link = {
        'url': db_note.path,
        'filename': f'{db_note.subject}.pdf'
    }

    return export_link


def build_note_download_url_with_token(note_to_process, user):
    user = security._authenticate_user(security.fake_users_db, 'johndoe',
                                       'secret')
    access_token_expires = security.timedelta(
        minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    note_to_process.path = f'{URL_BASE_PATH}notes/{note_to_process.id}/export?jwt={security.Token(access_token=access_token, token_type="bearer").access_token}'
    return note_to_process
