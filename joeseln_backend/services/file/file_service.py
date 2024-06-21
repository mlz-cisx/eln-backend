from copy import deepcopy

from fastapi.responses import FileResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from joeseln_backend.services.entry_path.entry_path_service import create_path, \
    create_entry
from joeseln_backend.auth import security
from joeseln_backend.models import models
from joeseln_backend.services.file.file_schemas import *
from joeseln_backend.ws.ws_client import transmit
from joeseln_backend.helper import db_ordering
from joeseln_backend.conf.base_conf import FILES_BASE_PATH, URL_BASE_PATH
from joeseln_backend.conf.mocks.mock_user import FAKE_USER_ID

from joeseln_backend.mylogging.root_logger import logger


def get_all_files(db: Session, params):
    # print(params.get('ordering'))
    order_params = db_ordering.get_order_params(ordering=params.get('ordering'))
    return db.query(models.File).filter_by(
        deleted=bool(params.get('deleted'))).order_by(
        text(order_params)).offset(params.get('offset')).limit(
        params.get('limit')).all()


def get_file(db: Session, file_pk):
    db_file = db.query(models.File).get(file_pk)

    db_file = build_download_url_with_token(file_to_process=deepcopy(db_file),
                                            user='foo')

    return db_file


def get_lb_pk_from_file(db: Session, file_pk):
    file = db.query(models.File).get(file_pk)
    elem = db.query(models.Labbookchildelement).get(file.elem_id)
    return elem.labbook_id


def create_file(db: Session, title: str,
                name: str, file_size: int, description: str, mime_type: str):
    file_path = f'{create_path(db=db)}'

    upload_entry_id = create_entry(db=db)
    db_file = models.File(version_number=0,
                          uploaded_file_entry_id=upload_entry_id,
                          # path in projects storage
                          path=file_path,
                          deleted=False,
                          # description title
                          title=title,
                          name=name,
                          original_filename=name,
                          display=name,
                          imported=False,
                          # editor content
                          description=description,
                          file_size=file_size,
                          mime_type=mime_type,
                          created_at=datetime.datetime.now(),
                          created_by_id=FAKE_USER_ID,
                          last_modified_at=datetime.datetime.now(),
                          last_modified_by_id=FAKE_USER_ID)

    db.add(db_file)
    db.commit()
    db.refresh(db_file)
    db.close()

    return db_file


def update_file(file_pk, db: Session, elem: FilePatch):
    db_file = db.query(models.File).get(file_pk)
    db_file.title = elem.title
    db_file.description = elem.description
    try:
        db.commit()
    except SQLAlchemyError as e:
        logger.error(e)
    db.refresh(db_file)
    transmit({'model_name': 'file', 'model_pk': str(file_pk)})
    return db_file


def process_file_upload_form(form, db, contents):
    # print(form)
    # print(len(contents))
    # print(form['path'].size)
    # print(form['path'].content_type)  # mime_type
    # print(form['path'].filename)  # is form[name]

    db_file = create_file(db=db, title=form['title'],
                          name=form['name'],
                          file_size=form['path'].size,
                          description=form[
                              'description'] if 'description' in form.keys() else None,
                          mime_type=form['path'].content_type)

    file_path = f'{FILES_BASE_PATH}{db_file.path}'

    with open(file_path, 'wb') as file:
        file.write(contents)
        file.close()

    db.close()

    ret_file = build_download_url_with_token(file_to_process=deepcopy(db_file),
                                             user='foo')

    return ret_file


def build_download_url_with_token(file_to_process, user):
    user = security.authenticate_user(security.fake_users_db, 'johndoe',
                                      'secret')
    access_token_expires = security.timedelta(
        minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    file_to_process.path = f'{URL_BASE_PATH}files/{file_to_process.id}/download?jwt={security.Token(access_token=access_token, token_type="bearer").access_token}'
    return file_to_process


def build_file_download_response(file_pk, db, jwt):
    db_file = db.query(models.File).get(file_pk)
    file_path = f'{FILES_BASE_PATH}{db_file.path}'
    value = FileResponse(file_path)

    return value


def get_file_export_link(db: Session, file_pk):
    db_file = db.query(models.File).get(file_pk)
    db_file = build_file_download_url_with_token(
        file_to_process=db_file,
        user='foo')
    export_link = {
        'url': db_file.path,
        'filename': f'{db_file.title}.pdf'
    }

    return export_link


def build_file_download_url_with_token(file_to_process, user):
    user = security.authenticate_user(security.fake_users_db, 'johndoe',
                                      'secret')
    access_token_expires = security.timedelta(
        minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    file_to_process.path = f'{URL_BASE_PATH}files/{file_to_process.id}/export?jwt={security.Token(access_token=access_token, token_type="bearer").access_token}'
    return file_to_process


def soft_delete_file(db: Session, file_pk, labbook_data):
    file_to_update = db.query(models.File).get(file_pk)
    file_to_update.deleted = True
    lb_elem = db.query(models.Labbookchildelement).get(file_to_update.elem_id)
    lb_elem.deleted = True
    try:
        db.commit()
    except SQLAlchemyError as e:
        logger.error(e)
        return file_to_update
    db.refresh(file_to_update)
    query = db.query(models.Labbookchildelement).filter_by(
        labbook_id=labbook_data.labbook_pk, deleted=False).all()
    if not query:
        try:
            transmit(
                {'model_name': 'labbook', 'model_pk': labbook_data.labbook_pk})
        except RuntimeError as e:
            logger.error(e)
    return file_to_update


def restore_file(db: Session, file_pk):
    file_to_update = db.query(models.File).get(file_pk)
    file_to_update.deleted = False
    lb_elem = db.query(models.Labbookchildelement).get(file_to_update.elem_id)
    lb_elem.deleted = False
    try:
        db.commit()
    except SQLAlchemyError as e:
        logger.error(e)
        return file_to_update
    db.refresh(file_to_update)
    return file_to_update
