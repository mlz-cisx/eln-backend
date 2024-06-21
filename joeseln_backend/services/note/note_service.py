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


def get_all_notes(db: Session, params):
    # print(params)
    order_params = db_ordering.get_order_params(ordering=params.get('ordering'))
    return db.query(models.Note).filter_by(
        deleted=bool(params.get('deleted'))).order_by(
        text(order_params)).offset(params.get('offset')).limit(
        params.get('limit')).all()


def get_note(db: Session, note_pk):
    return db.query(models.Note).get(note_pk)


def create_note(db: Session, note: NoteCreate):
    db_note = models.Note(version_number=0,
                          subject=note.subject,
                          content=note.content,
                          created_at=datetime.datetime.now(),
                          created_by_id=FAKE_USER_ID,
                          last_modified_at=datetime.datetime.now(),
                          last_modified_by_id=FAKE_USER_ID)

    db.add(db_note)
    db.commit()
    db.refresh(db_note)
    return db_note


def update_note(db: Session, note_pk, note: NoteCreate):
    note_to_update = db.query(models.Note).get(note_pk)
    note_to_update.subject = note.subject
    note_to_update.content = note.content
    try:
        db.commit()
    except SQLAlchemyError as e:
        print(e)
    db.refresh(note_to_update)
    return note_to_update


def soft_delete_note(db: Session, note_pk, labbook_data):
    note_to_update = db.query(models.Note).get(note_pk)
    note_to_update.deleted = True
    lb_elem = db.query(models.Labbookchildelement).get(note_to_update.elem_id)
    lb_elem.deleted = True
    try:
        db.commit()
    except SQLAlchemyError as e:
        print(e)
        return note_to_update
    db.refresh(note_to_update)
    query = db.query(models.Labbookchildelement).filter_by(
        labbook_id=labbook_data.labbook_pk, deleted=False).all()

    if not query:
        try:
            transmit(
                {'model_name': 'labbook', 'model_pk': labbook_data.labbook_pk})
        except RuntimeError as e:
            print(e)
    return note_to_update


def restore_note(db: Session, note_pk):
    note_to_update = db.query(models.Note).get(note_pk)
    note_to_update.deleted = False
    lb_elem = db.query(models.Labbookchildelement).get(note_to_update.elem_id)
    lb_elem.deleted = False
    try:
        db.commit()
    except SQLAlchemyError as e:
        print(e)
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
    user = security.authenticate_user(security.fake_users_db, 'johndoe',
                                      'secret')
    access_token_expires = security.timedelta(
        minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    note_to_process.path = f'{URL_BASE_PATH}notes/{note_to_process.id}/export?jwt={security.Token(access_token=access_token, token_type="bearer").access_token}'
    return note_to_process
