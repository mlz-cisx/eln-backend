from copy import deepcopy
import shutil
from fastapi.responses import FileResponse

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from joeseln_backend.ws.ws_client import transmit
from joeseln_backend.auth import security
from joeseln_backend.models import models
from joeseln_backend.helper import db_ordering
from joeseln_backend.services.entry_path.entry_path_service import create_path, \
    create_entry
from joeseln_backend.services.picture.picture_schemas import *
from joeseln_backend.conf.base_conf import PICTURES_BASE_PATH, URL_BASE_PATH
from joeseln_backend.conf.mocks.mock_user import FAKE_USER_ID


def get_all_pictures(db: Session, params):
    # print(params.get('ordering'))
    order_params = db_ordering.get_order_params(ordering=params.get('ordering'))
    return db.query(models.Picture).filter_by(
        deleted=bool(params.get('deleted'))).order_by(
        text(order_params)).offset(params.get('offset')).limit(
        params.get('limit')).all()


def get_picture(db: Session, picture_pk):
    db_picture = db.query(models.Picture).get(picture_pk)

    pic = build_download_url_with_token(
        picture=deepcopy(db_picture), user='foo')

    return pic


def get_picture_for_export(db: Session, picture_pk):
    db_picture = db.query(models.Picture).get(picture_pk)
    db_picture.rendered_image = f'{PICTURES_BASE_PATH}{db_picture.rendered_image}'
    return db_picture


def get_picture_filename(db: Session, picture_pk):
    pic = db.query(models.Picture).get(picture_pk)
    return pic.title


def get_picture_in_lb_init(db: Session, picture_pk, access_token, as_export):
    db_picture = db.query(models.Picture).get(picture_pk)

    picture = deepcopy(db_picture)

    picture.background_image = f'{URL_BASE_PATH}pictures/{picture.id}/bi_download?jwt={security.Token(access_token=access_token, token_type="bearer").access_token}'
    if as_export:
        picture.rendered_image = f'{PICTURES_BASE_PATH}{db_picture.rendered_image}'
    else:
        picture.rendered_image = f'{URL_BASE_PATH}pictures/{picture.id}/ri_download?jwt={security.Token(access_token=access_token, token_type="bearer").access_token}'

    picture.shapes_image = f'{URL_BASE_PATH}pictures/{picture.id}/shapes/'

    return picture


def get_lb_pk_from_picture(db: Session, picture_pk):
    pic = db.query(models.Picture).get(picture_pk)
    elem = db.query(models.Labbookchildelement).get(pic.elem_id)
    return elem.labbook_id


def copy_and_update_picture(db: Session, picture_pk):
    db_picture = db.query(models.Picture).get(picture_pk)

    old_ri_img_path = db_picture.rendered_image
    old_shapes_path = db_picture.shapes_image

    new_ri_img_path = f'{create_path(db=db)}'
    new_shapes_path = f'{create_path(db=db)}.json'

    shutil.copyfile(f'{PICTURES_BASE_PATH}{old_ri_img_path}',
                    f'{PICTURES_BASE_PATH}{new_ri_img_path}')
    shutil.copyfile(f'{PICTURES_BASE_PATH}{old_shapes_path}',
                    f'{PICTURES_BASE_PATH}{new_shapes_path}')

    db_picture.rendered_image = new_ri_img_path
    db_picture.shapes_image = new_shapes_path
    try:
        db.commit()
        db.refresh(db_picture)
    except SQLAlchemyError as e:
        print(e)

    return [old_ri_img_path,
            old_shapes_path]


def create_picture(db: Session, title: str, display: str,
                   width: int, height: int, size: int):
    bi_file_path = f'{create_path(db=db)}'
    ri_file_path = f'{create_path(db=db)}'
    shapes_path = f'{create_path(db=db)}.json'

    upload_entry_id = create_entry(db=db)
    db_picture = models.Picture(version_number=0,
                                uploaded_picture_entry_id=upload_entry_id,
                                title=title,
                                display=display,
                                width=width,
                                height=height,
                                background_image=bi_file_path,
                                background_image_size=size,
                                rendered_image=ri_file_path,
                                rendered_image_size=size,
                                shapes_image=shapes_path,
                                shapes_image_size=0,
                                created_at=datetime.datetime.now(),
                                created_by_id=FAKE_USER_ID,
                                last_modified_at=datetime.datetime.now(),
                                last_modified_by_id=FAKE_USER_ID)

    db.add(db_picture)
    db.commit()
    db.refresh(db_picture)
    db.close()

    return db_picture


def process_picture_upload_form(form, db, contents):
    db_picture = create_picture(db=db, title=form['title'],
                                display=form['background_image'].filename,
                                width=form['width'], height=form['height'],
                                size=form['background_image'].size)

    bi_img_path = f'{PICTURES_BASE_PATH}{db_picture.background_image}'
    ri_img_path = f'{PICTURES_BASE_PATH}{db_picture.rendered_image}'
    shapes_path = f'{PICTURES_BASE_PATH}{db_picture.shapes_image}'

    # print(filetype.guess(contents))

    with open(bi_img_path, 'wb') as image:
        image.write(contents)
        image.close()

    with open(ri_img_path, 'wb') as image:
        image.write(contents)
        image.close()

    with open(shapes_path, 'wb') as shapes:
        shapes.close()

    pic = build_download_url_with_token(
        picture=deepcopy(db_picture), user='foo')

    return pic


def process_sketch_upload_form(form, db, contents):
    # print(form['title'])
    # print(form['rendered_image'].filename)
    # print(form['width'])
    # print(form['height'])
    # print(form['rendered_image'].size)
    # print(filetype.guess(contents))

    db_picture = create_picture(db=db, title=form['title'],
                                display=form['title'],
                                width=form['width'], height=form['height'],
                                size=form['rendered_image'].size)

    bi_img_path = f'{PICTURES_BASE_PATH}{db_picture.background_image}'
    ri_img_path = f'{PICTURES_BASE_PATH}{db_picture.rendered_image}'
    shapes_path = f'{PICTURES_BASE_PATH}{db_picture.shapes_image}'

    with open(bi_img_path, 'wb') as image:
        image.write(contents)
        image.close()

    with open(ri_img_path, 'wb') as image:
        image.write(contents)
        image.close()

    with open(shapes_path, 'wb') as shapes:
        shapes.close()

    pic = build_download_url_with_token(
        picture=deepcopy(db_picture), user='foo')

    return pic


def update_picture(pk, form, db, bi_img_contents, ri_img_contents,
                   shapes_contents):
    db_picture = db.query(models.Picture).get(pk)
    db_picture.width = form['width']
    db_picture.height = form['height']
    try:
        db.commit()
    except SQLAlchemyError as e:
        print(e)

    db.refresh(db_picture)

    bi_img_path = f'{PICTURES_BASE_PATH}{db_picture.background_image}'
    ri_img_path = f'{PICTURES_BASE_PATH}{db_picture.rendered_image}'
    shapes_path = f'{PICTURES_BASE_PATH}{db_picture.shapes_image}'

    with open(ri_img_path, 'wb') as image:
        image.write(ri_img_contents)
        image.close()

    with open(shapes_path, 'wb') as shapes:
        shapes.write(shapes_contents)
        shapes.close()

    db.close()

    transmit({'model_name': 'picture', 'model_pk': str(pk)})
    pic = build_download_url_with_token(
        picture=deepcopy(db_picture), user='foo')

    return pic


def build_download_url_with_token(picture, user):
    user = security.authenticate_user(security.fake_users_db, 'johndoe',
                                      'secret')
    access_token_expires = security.timedelta(
        minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    picture.background_image = f'{URL_BASE_PATH}pictures/{picture.id}/bi_download?jwt={security.Token(access_token=access_token, token_type="bearer").access_token}'
    picture.rendered_image = f'{URL_BASE_PATH}pictures/{picture.id}/ri_download?jwt={security.Token(access_token=access_token, token_type="bearer").access_token}'
    picture.shapes_image = f'{URL_BASE_PATH}pictures/{picture.id}/shapes/'

    return picture


def build_bi_download_response(picture_pk, db, jwt):
    db_picture = db.query(models.Picture).get(picture_pk)
    bi_img_path = f'{PICTURES_BASE_PATH}{db_picture.background_image}'
    value = FileResponse(bi_img_path)

    return value


def build_ri_download_response(picture_pk, db, jwt):
    db_picture = db.query(models.Picture).get(picture_pk)
    ri_img_path = f'{PICTURES_BASE_PATH}{db_picture.rendered_image}'
    value = FileResponse(ri_img_path)

    return value


def build_shapes_response(picture_pk, db, jwt):
    db_picture = db.query(models.Picture).get(picture_pk)
    shapes_path = f'{PICTURES_BASE_PATH}{db_picture.shapes_image}'
    value = FileResponse(shapes_path)

    return value


def get_picture_export_link(db: Session, picture_pk):
    db_picture = db.query(models.Picture).get(picture_pk)
    db_picture = build_picture_download_url_with_token(
        picture_to_process=db_picture,
        user='foo')
    export_link = {
        'url': db_picture.path,
        'filename': f'{db_picture.title}.pdf'
    }

    return export_link


def build_picture_download_url_with_token(picture_to_process, user):
    user = security.authenticate_user(security.fake_users_db, 'johndoe',
                                      'secret')
    access_token_expires = security.timedelta(
        minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    picture_to_process.path = f'{URL_BASE_PATH}pictures/{picture_to_process.id}/export?jwt={security.Token(access_token=access_token, token_type="bearer").access_token}'
    return picture_to_process


def soft_delete_picture(db: Session, picture_pk, labbook_data):
    pic_to_update = db.query(models.Picture).get(picture_pk)
    pic_to_update.deleted = True
    lb_elem = db.query(models.Labbookchildelement).get(pic_to_update.elem_id)
    lb_elem.deleted = True
    try:
        db.commit()
    except SQLAlchemyError as e:
        print(e)
        return pic_to_update
    db.refresh(pic_to_update)
    query = db.query(models.Labbookchildelement).filter_by(
        labbook_id=labbook_data.labbook_pk, deleted=False).all()

    if not query:
        try:
            transmit(
                {'model_name': 'labbook', 'model_pk': labbook_data.labbook_pk})
        except RuntimeError as e:
            print(e)
    return pic_to_update


def restore_picture(db: Session, picture_pk):
    pic_to_update = db.query(models.Picture).get(picture_pk)
    pic_to_update.deleted = False
    lb_elem = db.query(models.Labbookchildelement).get(pic_to_update.elem_id)
    lb_elem.deleted = False
    try:
        db.commit()
    except SQLAlchemyError as e:
        print(e)
        return pic_to_update
    db.refresh(pic_to_update)
    return pic_to_update
