from copy import deepcopy
import shutil
from fastapi.responses import FileResponse

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from joeseln_backend.services.labbook.labbook_service import \
    check_for_labbook_access, get_all_labbook_ids_from_non_admin_user
from joeseln_backend.services.privileges.admin_privileges.privileges_service import \
    ADMIN
from joeseln_backend.services.privileges.privileges_service import \
    create_pic_privileges
from joeseln_backend.services.user_to_group.user_to_group_service import \
    check_for_admin_role, get_user_group_roles_with_match, get_user_group_roles
from joeseln_backend.ws.ws_client import transmit
from joeseln_backend.auth import security
from joeseln_backend.models import models
from joeseln_backend.helper import db_ordering
from joeseln_backend.services.entry_path.entry_path_service import create_path, \
    create_entry
from joeseln_backend.services.picture.picture_schemas import *
from joeseln_backend.conf.base_conf import PICTURES_BASE_PATH, URL_BASE_PATH, \
    LABBOOK_QUERY_MODE
from joeseln_backend.services.comment.comment_schemas import Comment

from joeseln_backend.mylogging.root_logger import logger


def get_all_pictures(db: Session, params, user):
    # print(params.get('ordering'))
    order_params = db_ordering.get_order_params(ordering=params.get('ordering'))
    if check_for_admin_role(db=db, username=user.username):
        pics =  db.query(models.Picture).filter_by(
            deleted=bool(params.get('deleted'))).order_by(
            text(order_params)).offset(params.get('offset')).limit(
            params.get('limit')).all()
        for pic in pics:
            db_user_created = db.query(models.User).get(pic.created_by_id)
            db_user_modified = db.query(models.User).get(
                pic.last_modified_by_id)
            pic.created_by = db_user_created
            pic.last_modified_by = db_user_modified

        return pics

    labbook_ids = get_all_labbook_ids_from_non_admin_user(db=db, user=user)

    pics = db.query(models.Picture).filter_by(
        deleted=bool(params.get('deleted'))). \
        join(models.Labbookchildelement,
             models.Picture.elem_id ==
             models.Labbookchildelement.id).filter(
        models.Labbookchildelement.labbook_id.in_(labbook_ids)).order_by(
        text('picture.' + order_params)).offset(
        params.get('offset')).limit(
        params.get('limit')).all()

    for pic in pics:
        db_user_created = db.query(models.User).get(pic.created_by_id)
        db_user_modified = db.query(models.User).get(
            pic.last_modified_by_id)
        pic.created_by = db_user_created
        pic.last_modified_by = db_user_modified

    return pics


def get_picture(db: Session, picture_pk, user):
    db_picture = db.query(models.Picture).get(picture_pk)
    db_user_created = db.query(models.User).get(db_picture.created_by_id)
    db_user_modified = db.query(models.User).get(db_picture.last_modified_by_id)
    db_picture.created_by = db_user_created
    db_picture.last_modified_by = db_user_modified

    pic = build_download_url_with_token(
        picture=deepcopy(db_picture), user=user)

    return pic


def get_picture_with_privileges(db: Session, picture_pk, user):
    db_picture = db.query(models.Picture).get(picture_pk)
    db_user_created = db.query(models.User).get(db_picture.created_by_id)
    db_user_modified = db.query(models.User).get(db_picture.last_modified_by_id)
    db_picture.created_by = db_user_created
    db_picture.last_modified_by = db_user_modified

    pic = build_download_url_with_token(
        picture=deepcopy(db_picture), user=user)

    if check_for_admin_role(db=db, username=user.username):
        return {'privileges': ADMIN,
                'picture': pic}

    lb_elem = db.query(models.Labbookchildelement).get(db_picture.elem_id)
    if not check_for_labbook_access(db=db, labbook_pk=lb_elem.labbook_id,
                                    user=user):
        return None

    db_lb = db.query(models.Labbook).get(lb_elem.labbook_id)
    db_pic_creator = db.query(models.User).get(db_picture.created_by_id)

    picture_created_by = 'USER'
    if db_pic_creator.admin:
        picture_created_by = 'ADMIN'

    if db_lb:
        if LABBOOK_QUERY_MODE == 'match':
            user_roles = get_user_group_roles_with_match(db=db,
                                                         username=user.username,
                                                         groupname=db_lb.title)
            privileges = create_pic_privileges(created_by=picture_created_by,
                                               user_roles=user_roles)

        else:
            user_roles = get_user_group_roles(db=db,
                                              username=user.username,
                                              groupname=db_lb.title)
            privileges = create_pic_privileges(created_by=picture_created_by,
                                               user_roles=user_roles)

        return {'privileges': privileges, 'picture': pic}

    return None


def get_picture_relations(db: Session, picture_pk, params):
    if not params:
        relations = db.query(models.Relation).filter_by(
            right_object_id=picture_pk, deleted=False).order_by(
            models.Relation.created_at).all()
    else:
        order_params = db_ordering.get_order_params(
            ordering=params.get('ordering'))

        relations = db.query(models.Relation).filter_by(
            right_object_id=picture_pk, deleted=False).order_by(
            text(order_params)).offset(params.get('offset')).limit(
            params.get('limit')).all()

    for rel in relations:
        if rel.left_content_type == 70:
            db_comment = db.query(models.Comment).get(rel.left_object_id)

            db_user_created = db.query(models.User).get(
                db_comment.created_by_id)
            db_user_modified = db.query(models.User).get(
                db_comment.last_modified_by_id)
            rel.created_by = db_user_created
            rel.last_modified_by = db_user_modified
            db_comment.created_by = db_user_created
            db_comment.last_modified_by = db_user_modified
            rel.left_content_object = Comment.parse_obj(db_comment)
        else:
            rel.left_content_object = None
        db_picture = db.query(models.Picture).get(picture_pk)
        db_user_created = db.query(models.User).get(db_picture.created_by_id)
        db_user_modified = db.query(models.User).get(
            db_picture.last_modified_by_id)
        db_picture.created_by = db_user_created
        db_picture.last_modified_by = db_user_modified
        rel.right_content_object = db_picture

    return relations


def delete_picture_relation(db: Session, picture_pk, relation_pk):
    db_relation = db.query(models.Relation).get(relation_pk)
    db_relation.deleted = True
    try:
        db.commit()
    except SQLAlchemyError as e:
        logger.error(e)
        db.close()
        return
    db.refresh(db_relation)

    return get_picture_relations(db=db, picture_pk=picture_pk, params='')


def get_picture_related_comments_count(db: Session, picture_pk, user):
    relations_count = db.query(models.Relation).filter_by(
        right_object_id=picture_pk, deleted=False, left_content_type=70).count()

    return relations_count


def get_picture_for_export(db: Session, picture_pk):
    db_picture = db.query(models.Picture).get(picture_pk)
    db_user_created = db.query(models.User).get(db_picture.created_by_id)
    db_user_modified = db.query(models.User).get(db_picture.last_modified_by_id)
    db_picture.created_by = db_user_created
    db_picture.last_modified_by = db_user_modified
    db_picture.rendered_image = f'{PICTURES_BASE_PATH}{db_picture.rendered_image}'
    return db_picture


def get_picture_filename(db: Session, picture_pk):
    pic = db.query(models.Picture).get(picture_pk)
    return pic.title


def get_picture_in_lb_init(db: Session, picture_pk, access_token, as_export):
    db_picture = db.query(models.Picture).get(picture_pk)

    db_user_created = db.query(models.User).get(db_picture.created_by_id)
    db_user_modified = db.query(models.User).get(db_picture.last_modified_by_id)
    db_picture.created_by = db_user_created
    db_picture.last_modified_by = db_user_modified

    picture = deepcopy(db_picture)

    picture.background_image = f'{URL_BASE_PATH}pictures/{picture.id}/bi_download?jwt={security.Token(access_token=access_token, token_type="bearer").access_token}'
    if as_export:
        picture.rendered_image = f'{PICTURES_BASE_PATH}{db_picture.rendered_image}'
    else:
        picture.rendered_image = f'{URL_BASE_PATH}pictures/{picture.id}/ri_download?jwt={security.Token(access_token=access_token, token_type="bearer").access_token}'

    picture.shapes_image = f'{URL_BASE_PATH}pictures/{picture.id}/shapes?jwt={security.Token(access_token=access_token, token_type="bearer").access_token}'

    return picture


def get_lb_pk_from_picture(db: Session, picture_pk):
    pic = db.query(models.Picture).get(picture_pk)
    elem = db.query(models.Labbookchildelement).get(pic.elem_id)
    return elem.labbook_id


def copy_and_update_picture(db: Session, picture_pk, restored_ri=None,
                            restored_shapes=None):
    new_ri_img_path = f'{create_path(db=db)}'
    new_shapes_path = f'{create_path(db=db)}.json'
    db_picture = db.query(models.Picture).get(picture_pk)
    if restored_ri is not None:
        old_ri_img_path = restored_ri
        old_shapes_path = restored_shapes
    else:
        old_ri_img_path = db_picture.rendered_image
        old_shapes_path = db_picture.shapes_image

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
        logger.error(e)
        db.close()

    return [old_ri_img_path,
            old_shapes_path]


def create_picture(db: Session, title: str, display: str,
                   width: int, height: int, size: int, user):
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
                                created_by_id=user.id,
                                last_modified_at=datetime.datetime.now(),
                                last_modified_by_id=user.id)

    db.add(db_picture)
    try:
        db.commit()
    except SQLAlchemyError as e:
        logger.error(e)
        db.close()
        return db_picture
    db.refresh(db_picture)
    db.close()

    return db_picture


def process_picture_upload_form(form, db, contents, user):
    db_picture = create_picture(db=db, title=form['title'],
                                display=form['background_image'].filename,
                                width=form['width'], height=form['height'],
                                size=form['background_image'].size, user=user)

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
        picture=deepcopy(db_picture), user=user)

    pic.created_by = user
    pic.last_modified_by = user

    return pic


def process_sketch_upload_form(form, db, contents, user):
    # print(form['title'])
    # print(form['rendered_image'].filename)
    # print(form['width'])
    # print(form['height'])
    # print(form['rendered_image'].size)
    # print(filetype.guess(contents))

    db_picture = create_picture(db=db, title=form['title'],
                                display=form['title'],
                                width=form['width'], height=form['height'],
                                size=form['rendered_image'].size, user=user)

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
        picture=deepcopy(db_picture), user=user)

    return pic


def update_picture(pk, form, db, bi_img_contents, ri_img_contents,
                   shapes_contents, user):
    db_picture = db.query(models.Picture).get(pk)
    db_picture.width = form['width']
    db_picture.height = form['height']
    db_picture.last_modified_at = datetime.datetime.now()
    db_picture.last_modified_by_id = user.id

    db_user_created = db.query(models.User).get(db_picture.created_by_id)


    lb_elem = db.query(models.Labbookchildelement).get(db_picture.elem_id)
    lb_elem.last_modified_at = datetime.datetime.now()
    lb_elem.last_modified_by_id = user.id

    lb_to_update = db.query(models.Labbook).get(lb_elem.labbook_id)
    lb_to_update.last_modified_at = datetime.datetime.now()
    lb_to_update.last_modified_by_id = user.id
    try:
        db.commit()
    except SQLAlchemyError as e:
        logger.error(e)
        db.close()
        return

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
        picture=deepcopy(db_picture), user=user)

    pic.created_by = db_user_created
    pic.last_modified_by = user

    return pic


def build_download_url_with_token(picture, user):
    access_token_expires = security.timedelta(
        minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    picture.background_image = f'{URL_BASE_PATH}pictures/{picture.id}/bi_download?jwt={security.Token(access_token=access_token, token_type="bearer").access_token}'
    picture.rendered_image = f'{URL_BASE_PATH}pictures/{picture.id}/ri_download?jwt={security.Token(access_token=access_token, token_type="bearer").access_token}'
    picture.shapes_image = f'{URL_BASE_PATH}pictures/{picture.id}/shapes?jwt={security.Token(access_token=access_token, token_type="bearer").access_token}'

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


def get_picture_export_link(db: Session, picture_pk, user):
    db_picture = db.query(models.Picture).get(picture_pk)
    db_picture = build_picture_download_url_with_token(
        picture_to_process=db_picture,
        user=user)
    lb_elem = db.query(models.Labbookchildelement).get(db_picture.elem_id)

    export_link = {
        'url': db_picture.path,
        'filename': f'{db_picture.title}.pdf'
    }

    if check_for_admin_role(db=db,
                            username=user.username) or check_for_labbook_access(
        db=db, labbook_pk=lb_elem.labbook_id,
        user=user):
        return export_link

    return None


def build_picture_download_url_with_token(picture_to_process, user):
    access_token_expires = security.timedelta(
        minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    picture_to_process.path = f'{URL_BASE_PATH}pictures/{picture_to_process.id}/export?jwt={security.Token(access_token=access_token, token_type="bearer").access_token}'
    return picture_to_process


def soft_delete_picture(db: Session, picture_pk, labbook_data, user):
    pic_to_update = db.query(models.Picture).get(picture_pk)
    pic_to_update.deleted = True
    pic_to_update.last_modified_at = datetime.datetime.now()
    pic_to_update.last_modified_by_id = user.id

    lb_elem = db.query(models.Labbookchildelement).get(pic_to_update.elem_id)
    lb_elem.deleted = True
    lb_elem.last_modified_at = datetime.datetime.now()
    lb_elem.last_modified_by_id = user.id

    lb_to_update = db.query(models.Labbook).get(lb_elem.labbook_id)
    lb_to_update.last_modified_at = datetime.datetime.now()
    lb_to_update.last_modified_by_id = user.id
    try:
        db.commit()
    except SQLAlchemyError as e:
        logger.error(e)
        db.close()
        return pic_to_update
    db.refresh(pic_to_update)
    query = db.query(models.Labbookchildelement).filter_by(
        labbook_id=labbook_data.labbook_pk, deleted=False).all()

    if not query:
        try:
            transmit(
                {'model_name': 'labbook', 'model_pk': labbook_data.labbook_pk})
        except RuntimeError as e:
            logger.error(e)
    return pic_to_update


def restore_picture(db: Session, picture_pk, user):
    pic_to_update = db.query(models.Picture).get(picture_pk)
    pic_to_update.deleted = False
    pic_to_update.last_modified_at = datetime.datetime.now()
    pic_to_update.last_modified_by_id = user.id

    lb_elem = db.query(models.Labbookchildelement).get(pic_to_update.elem_id)
    lb_elem.deleted = False
    lb_elem.last_modified_at = datetime.datetime.now()
    lb_elem.last_modified_by_id = user.id

    lb_to_update = db.query(models.Labbook).get(lb_elem.labbook_id)
    lb_to_update.last_modified_at = datetime.datetime.now()
    lb_to_update.last_modified_by_id = user.id
    try:
        db.commit()
    except SQLAlchemyError as e:
        logger.error(e)
        db.close()
        return pic_to_update
    db.refresh(pic_to_update)
    return pic_to_update
