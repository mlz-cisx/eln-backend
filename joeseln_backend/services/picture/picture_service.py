import base64
import datetime
import gzip
import io
import json
import pathlib
import sys
from copy import deepcopy

from fastapi.exceptions import HTTPException
from fastapi.responses import FileResponse
from PIL import Image
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from typesense.client import Client
from typesense.exceptions import TypesenseClientError

from joeseln_backend.auth import security
from joeseln_backend.auth.security import get_user_from_jwt
from joeseln_backend.conf.base_conf import (
    ELEM_MAXIMUM_SIZE,
    LABBOOK_QUERY_MODE,
    PICTURES_BASE_PATH,
    URL_BASE_PATH,
)
from joeseln_backend.full_text_search.typesense_service import (
    update_delete_status_typesense,
)
from joeseln_backend.helper import db_ordering
from joeseln_backend.models import models
from joeseln_backend.mylogging.root_logger import logger
from joeseln_backend.services.comment.comment_schemas import Comment
from joeseln_backend.services.entry_path.entry_path_service import (
    create_entry,
    create_path,
)
from joeseln_backend.services.history.history_service import create_history_entry
from joeseln_backend.services.labbook.labbook_service import (
    check_for_labbook_access,
    check_for_labbook_admin_access,
    get_all_labbook_ids_from_non_admin_user,
)
from joeseln_backend.services.picture.picture_schemas import (
    PictureUpload,
    UpdatePictureTitle,
)
from joeseln_backend.services.privileges.admin_privileges.privileges_service import (
    ADMIN,
)
from joeseln_backend.services.privileges.privileges_service import (
    create_pic_privileges,
    create_strict_privileges,
)
from joeseln_backend.services.user_to_group.user_to_group_service import (
    check_for_admin_role_with_user_id,
    check_for_guest_role,
    get_user_group_roles,
    get_user_group_roles_with_match,
)
from joeseln_backend.ws.ws_client import transmit


def get_all_pictures(db: Session, params, user):
    # print(params.get('ordering'))
    order_params = db_ordering.get_order_params(ordering=params.get('ordering'))
    if user.admin:
        if params.get('search'):
            search_text = params.get('search')
            pics = db.query(models.Picture).filter_by(
                deleted=bool(params.get('deleted'))).join(
                models.Labbookchildelement,
                models.Picture.elem_id ==
                models.Labbookchildelement.id).join(models.Labbook,
                                                    models.Labbook.id ==
                                                    models.Labbookchildelement.labbook_id). \
                filter(or_
                       (models.Labbook.title.ilike(f'%{search_text}%'),
                        models.Picture.title.ilike(
                            f'%{search_text}%')),
                       models.Labbook.deleted == False).order_by(
                text('picture.' + order_params)).offset(
                params.get('offset')).limit(
                params.get('limit')).all()
        else:
            pics = db.query(models.Picture).filter_by(
                deleted=bool(params.get('deleted'))).join(
                models.Labbookchildelement,
                models.Picture.elem_id ==
                models.Labbookchildelement.id).join(models.Labbook,
                                                    models.Labbook.id ==
                                                    models.Labbookchildelement.labbook_id).filter(
                models.Labbook.deleted == False).order_by(
                text('picture.' + order_params)).offset(
                params.get('offset')).limit(
                params.get('limit')).all()
        for pic in pics:
            db_user_created = db.query(models.User).get(pic.created_by_id)
            db_user_modified = db.query(models.User).get(
                pic.last_modified_by_id)
            pic.created_by = db_user_created
            pic.last_modified_by = db_user_modified

            try:
                lb_elem = db.query(models.Labbookchildelement).get(pic.elem_id)
                lb = db.query(models.Labbook).get(lb_elem.labbook_id)
                pic.lb_title = lb.title
            except SQLAlchemyError:
                pic.lb_title = 'None'

        return pics

    labbook_ids = get_all_labbook_ids_from_non_admin_user(db=db, user=user)

    if params.get('search'):
        search_text = params.get('search')
        pics = db.query(models.Picture).filter_by(
            deleted=bool(params.get('deleted'))).join(
            models.Labbookchildelement,
            models.Picture.elem_id ==
            models.Labbookchildelement.id).filter(
            models.Labbookchildelement.labbook_id.in_(labbook_ids)).join(
            models.Labbook,
            models.Labbook.id ==
            models.Labbookchildelement.labbook_id). \
            filter(or_
                   (models.Labbook.title.ilike(f'%{search_text}%'),
                    models.Picture.title.ilike(f'%{search_text}%')),
                   models.Labbook.deleted == False).order_by(
            text('picture.' + order_params)).offset(
            params.get('offset')).limit(
            params.get('limit')).all()
    else:
        pics = db.query(models.Picture).filter_by(
            deleted=bool(params.get('deleted'))). \
            join(models.Labbookchildelement,
                 models.Picture.elem_id ==
                 models.Labbookchildelement.id).join(models.Labbook,
                                                     models.Labbook.id ==
                                                     models.Labbookchildelement.labbook_id).filter(
            models.Labbookchildelement.labbook_id.in_(labbook_ids),
            models.Labbook.deleted == False).order_by(
            text('picture.' + order_params)).offset(
            params.get('offset')).limit(
            params.get('limit')).all()

    for pic in pics:
        db_user_created = db.query(models.User).get(pic.created_by_id)
        db_user_modified = db.query(models.User).get(
            pic.last_modified_by_id)
        pic.created_by = db_user_created
        pic.last_modified_by = db_user_modified

        try:
            lb_elem = db.query(models.Labbookchildelement).get(pic.elem_id)
            lb = db.query(models.Labbook).get(lb_elem.labbook_id)
            pic.lb_title = lb.title
        except SQLAlchemyError:
            pic.lb_title = 'None'

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


def get_canvas_content(db: Session, picture_pk, user):
    db_picture = db.query(models.Picture).get(picture_pk)
    if db_picture:
        lb_elem = db.query(models.Labbookchildelement).get(db_picture.elem_id)
        if not lb_elem:
            return None
        if user.admin:
            return db_picture
        if not check_for_labbook_access(db=db, labbook_pk=lb_elem.labbook_id,
                                        user=user):
            return None
        return db_picture
    return None


def update_title(db: Session, picture_pk, user,
                 pic_payload: UpdatePictureTitle):
    db_picture = db.query(models.Picture).get(picture_pk)

    old_title = db_picture.title

    db_picture.title = pic_payload.title
    db_picture.last_modified_at = datetime.datetime.now()
    db_picture.last_modified_by_id = user.id

    lb_elem = db.query(models.Labbookchildelement).get(db_picture.elem_id)

    lb_to_update = db.query(models.Labbook).get(lb_elem.labbook_id)
    lb_to_update.last_modified_at = datetime.datetime.now()
    lb_to_update.last_modified_by_id = user.id

    db_user_created = db.query(models.User).get(db_picture.created_by_id)

    # picture created by instrument
    if db_user_created.admin and check_for_labbook_admin_access(db=db,
                                                                labbook_pk=lb_elem.labbook_id,
                                                                user=user):
        try:
            db.commit()
        except SQLAlchemyError as e:
            logger.error(e)
            db.close()
            return
        db.refresh(db_picture)
        db_user_created = db.query(models.User).get(db_picture.created_by_id)
        db_picture.created_by = db_user_created
        db_picture.last_modified_by = user
        db.close()
        transmit({'model_name': 'picture_title', 'model_pk': str(picture_pk)})
        pic = build_download_url_with_token(
            picture=deepcopy(db_picture), user=user)

        changerecords = [['title', old_title, pic_payload.title]]
        # changeset_types:
        # U : edited/updated, R : restored, S: trashed , I initialized/created
        create_history_entry(db=db,
                             elem_id=picture_pk,
                             user=user,
                             object_type_id=40,
                             changeset_type='U',
                             changerecords=changerecords)

        return pic

    # picture not created by an admin
    if not db_user_created.admin and check_for_labbook_access(db=db,
                                                              labbook_pk=lb_elem.labbook_id,
                                                              user=user):

        try:
            db.commit()
        except SQLAlchemyError as e:
            logger.error(e)
            db.close()
            return

        db.refresh(db_picture)
        db_user_created = db.query(models.User).get(db_picture.created_by_id)
        db_picture.created_by = db_user_created
        db_picture.last_modified_by = user
        db.close()
        transmit({'model_name': 'picture_title', 'model_pk': str(picture_pk)})
        pic = build_download_url_with_token(
            picture=deepcopy(db_picture), user=user)

        changerecords = [['title', old_title, pic_payload.title]]
        # changeset_types:
        # U : edited/updated, R : restored, S: trashed , I initialized/created
        create_history_entry(db=db,
                             elem_id=picture_pk,
                             user=user,
                             object_type_id=40,
                             changeset_type='U',
                             changerecords=changerecords)

        return pic

    return None


def update_canvas_content(db: Session, tsClient: Client, picture_pk, user,
                          pic_payload: PictureUpload):
    db_picture = db.query(models.Picture).get(picture_pk)
    db_picture.canvas_content = pic_payload.canvas_content
    db_picture.last_modified_at = datetime.datetime.now()
    db_picture.last_modified_by_id = user.id

    lb_elem = db.query(models.Labbookchildelement).get(db_picture.elem_id)

    lb_to_update = db.query(models.Labbook).get(lb_elem.labbook_id)
    lb_to_update.last_modified_at = datetime.datetime.now()
    lb_to_update.last_modified_by_id = user.id

    # store texts into typesense for searching
    objects = json.loads(pic_payload.canvas_content)['objects']
    texts = ' '.join([obj.get('text') for obj in objects if 'text' in obj])
    update_pic_typesense(db_picture, texts, tsClient)

    if not user.admin and lb_to_update.strict_mode \
            and user.id != db_picture.created_by_id:
        return None

    # picture can be edited by every user if not in strict mode
    if check_for_labbook_access(db=db,
                                labbook_pk=lb_elem.labbook_id,
                                user=user):

        try:
            db.commit()
        except SQLAlchemyError as e:
            logger.error(e)
            db.close()
            return

        db.refresh(db_picture)
        db_user_created = db.query(models.User).get(db_picture.created_by_id)
        db_picture.created_by = db_user_created
        db_picture.last_modified_by = user
        db.close()
        transmit({'model_name': 'picture_content', 'origin': pic_payload.origin,
                  'model_pk': str(picture_pk)})
        pic = build_download_url_with_token(
            picture=deepcopy(db_picture), user=user)

        changerecords = [['canvas_content', '...', '...']]
        # changeset_types:
        # U : edited/updated, R : restored, S: trashed , I initialized/created
        create_history_entry(db=db,
                             elem_id=picture_pk,
                             user=user,
                             object_type_id=40,
                             changeset_type='U',
                             changerecords=changerecords)

        return pic

    return None


def get_all_deleted_pics(db: Session):
    pics = db.query(models.Picture).filter_by(
        deleted=True).order_by(text('title asc')).all()
    return pics


def get_picture_with_privileges(db: Session, picture_pk, user, If_None_Match):
    db_picture = db.query(models.Picture).get(picture_pk)
    if db_picture:
        etag = f'{db_picture.id}-{db_picture.last_modified_at}'
        if If_None_Match == etag:
            raise HTTPException(status_code=304) 

        db_user_created = db.query(models.User).get(db_picture.created_by_id)
        db_user_modified = db.query(models.User).get(
            db_picture.last_modified_by_id)
        db_picture.created_by = db_user_created
        db_picture.last_modified_by = db_user_modified

        pic = build_download_url_with_token(
            picture=deepcopy(db_picture), user=user)

        if user.admin:
            return {'content': {'privileges': ADMIN,
                                'picture': pic},
                    'etag': etag}

        lb_elem = db.query(models.Labbookchildelement).get(db_picture.elem_id)

        if not lb_elem:
            return None

        if not check_for_labbook_access(db=db, labbook_pk=lb_elem.labbook_id,
                                        user=user):
            return None

        db_lb = db.query(models.Labbook).get(lb_elem.labbook_id)
        db_pic_creator = db.query(models.User).get(db_picture.created_by_id)

        picture_created_by = 'USER'
        if db_pic_creator.admin:
            picture_created_by = 'ADMIN'

        if db_lb and not db_lb.strict_mode:
            if LABBOOK_QUERY_MODE == 'match':
                user_roles = get_user_group_roles_with_match(db=db,
                                                             username=user.username,
                                                             groupname=db_lb.title)
                privileges = create_pic_privileges(
                    created_by=picture_created_by,
                    user_roles=user_roles)

            else:
                user_roles = get_user_group_roles(db=db,
                                                  username=user.username,
                                                  groupname=db_lb.title)
                privileges = create_pic_privileges(
                    created_by=picture_created_by,
                    user_roles=user_roles)

            return {'content':{'privileges': privileges, 'picture': pic}, 'etag': etag} 
        if db_lb and db_lb.strict_mode and user.id == db_pic_creator.id:
            privileges = create_strict_privileges(
                created_by='SELF')
            return {'content':{'privileges': privileges, 'picture': pic}, 'etag': etag}

        if db_lb and db_lb.strict_mode and user.id != db_pic_creator.id:
            privileges = create_strict_privileges(
                created_by='ANOTHER')
            return {'content':{'privileges': privileges, 'picture': pic}, 'etag': etag}
        return None
    return None


def get_picture_relations(db: Session, picture_pk, params, user):
    db_picture = db.query(models.Picture).get(picture_pk)
    lb_elem = db.query(models.Labbookchildelement).get(db_picture.elem_id)
    if check_for_labbook_access(db=db, labbook_pk=lb_elem.labbook_id,
                                user=user):

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

            db_user_created = db.query(models.User).get(
                db_picture.created_by_id)
            db_user_modified = db.query(models.User).get(
                db_picture.last_modified_by_id)
            db_picture.created_by = db_user_created
            db_picture.last_modified_by = db_user_modified
            rel.right_content_object = db_picture

        return relations

    return []


def delete_picture_relation(db: Session, picture_pk, relation_pk, user):
    db_pic = db.query(models.Picture).get(picture_pk)
    lb_elem = db.query(models.Labbookchildelement).get(db_pic.elem_id)
    db_relation = db.query(models.Relation).get(relation_pk)
    # comment can only be deteled by its creator or groupadmins
    if (
        db_relation
        and lb_elem
        and (
            db_relation.created_by_id == user.id
            or check_for_labbook_admin_access(
                db=db, labbook_pk=lb_elem.labbook_id, user=user
            )
        )
    ):
        db_relation.deleted = True
        try:
            db.commit()
        except SQLAlchemyError as e:
            logger.error(e)
            db.close()
            return
        db.refresh(db_relation)

        comments_count = db.query(models.Relation).filter(
            models.Relation.right_object_id == picture_pk,
            models.Relation.deleted == False).count()

        transmit({'model_name': 'comments', 'model_pk': str(picture_pk),
                  'comments_count': comments_count})

        return True
    return None


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
    elem = db.query(models.Labbookchildelement).get(db_picture.elem_id)
    db_picture.canvas_width = \
        round(84 * elem.width * 0.9)  # 84px default width per col
    db_picture.canvas_height = \
        round(36 * elem.height * 0.8)  # 36px default height per row
    return db_picture


def get_picture_filename(db: Session, picture_pk):
    pic = db.query(models.Picture).get(picture_pk)
    return pic.title




def get_picture_for_zip_export(db: Session, picture_pk):
    db_picture = db.query(models.Picture).get(picture_pk)
    db_user_created = db.query(models.User).get(db_picture.created_by_id)
    db_user_modified = db.query(models.User).get(db_picture.last_modified_by_id)
    db_picture.created_by = db_user_created
    db_picture.last_modified_by = db_user_modified
    db_picture.background_image = f'{PICTURES_BASE_PATH}{db_picture.background_image}'

    return db_picture


def get_lb_pk_from_picture(db: Session, picture_pk):
    pic = db.query(models.Picture).get(picture_pk)
    elem = db.query(models.Labbookchildelement).get(pic.elem_id)
    return elem.labbook_id


def create_picture(db: Session, title: str, display: str,
                   user, size: int = 0, canvas_content: str = None):
    canvas_content = '{"version":"6.9.0","objects":[],"background":"#F8F8FF"}' \
        if canvas_content is None else canvas_content
    if size > ELEM_MAXIMUM_SIZE << 10 or sys.getsizeof(
            canvas_content) > ELEM_MAXIMUM_SIZE << 10:
        return

    bi_file_path = f'{create_path(db=db)}'

    upload_entry_id = create_entry(db=db)
    db_picture = models.Picture(version_number=0,
                                uploaded_picture_entry_id=upload_entry_id,
                                title=title,
                                display=display,
                                background_image=bi_file_path,
                                canvas_content=canvas_content,
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

    # changerecord = [field_name,old_value,new_value]
    # changerecords = [changerecord, changerecord, .....]
    changerecords = [['title', None, title],
                     ['display', None, display]]
    # changeset_types:
    # U : edited/updated, R : restored, S: trashed , I initialized/created
    create_history_entry(db=db,
                         elem_id=db_picture.id,
                         user=user,
                         object_type_id=40,
                         changeset_type='I',
                         changerecords=changerecords)

    return db_picture


def clone_picture(db, bi_img_contents, info, user):
    if not user.admin:
        return
    info = json.loads(info)
    db_picture = create_picture(db=db,
                                title=info['title'],
                                display=info['display'],
                                canvas_content=info['canvas_content'],
                                user=user)

    if not db_picture:
        return None

    bi_img_path = f'{PICTURES_BASE_PATH}{db_picture.background_image}'


    with open(bi_img_path, 'wb') as image:
        image.write(bi_img_contents)
        image.close()


    pic = build_download_url_with_token(
        picture=deepcopy(db_picture), user=user)

    pic.created_by = user
    pic.last_modified_by = user

    return pic


def process_picture_upload_form(form, db, contents, user):
    db_picture = create_picture(db=db, title=form['title'],
                                display=form['background_image'].filename,
                                size=form['background_image'].size, user=user)

    if not db_picture:
        return None

    bi_img_path = f'{PICTURES_BASE_PATH}{db_picture.background_image}'

    base64_string = base64.b64encode(contents).decode("utf-8")

    with open(bi_img_path, 'wb') as image:
        image.write(contents)
        image.close()


    deepcopied_pic = deepcopy(db_picture)
    pic_to_update = db.query(models.Picture).get(deepcopied_pic.id)
    pic_to_update.canvas_content = get_canvas_content_with_imgbase64(
        img_src=base64_string)
    try:
        db.commit()
    except SQLAlchemyError as e:
        logger.error(e)
        db.close()
        return

    pic = build_download_url_with_token(
        picture=deepcopied_pic, user=user)

    pic.created_by = user
    pic.last_modified_by = user

    return pic


async def process_sketch_upload_form(form, db, user):
    content = None
    canvas_content = form.get("canvas_content")
    if canvas_content:
        info_bytes = await canvas_content.read()
        content = gzip.decompress(info_bytes).decode("utf-8")

    db_picture = create_picture(db=db, title=form['title'],
                                display=form['title'],
                                user=user, canvas_content=content)


    bi_img_path = f'{PICTURES_BASE_PATH}{db_picture.background_image}'

    with open(bi_img_path, 'wb'):
        pass  # do nothing, file is created empty

    pic = build_download_url_with_token(
        picture=deepcopy(db_picture), user=user)

    pic.created_by = user
    pic.last_modified_by = user

    return pic


def update_pic_typesense(pic: models.Picture, content: str, typesense: Client):
    try:
        document = {
                'subject': pic.title, 
                'content': content, 
                'last_modified_at': int(pic.last_modified_at.timestamp())}
        typesense.collections['pictures'].documents[str(pic.id)].update(document)
    except TypesenseClientError as e:
        logger.error(e)


def build_download_url_with_token(picture, user):
    access_token = security.build_download_token(user, picture.id)
    picture.background_image = f'{URL_BASE_PATH}pictures/{picture.id}/bi_download/?jwt={security.Token(access_token=access_token, token_type="bearer").access_token}'

    return picture


def build_bi_download_response(picture_pk, db, jwt):
    user = get_user_from_jwt(db=db, token=jwt)
    if user is None:
        return
    db_picture = db.query(models.Picture).get(picture_pk)
    bi_img_path = f'{PICTURES_BASE_PATH}{db_picture.background_image}'
    value = FileResponse(bi_img_path)

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

    if user.admin or check_for_labbook_access(
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


# needs to be heavily factorized
def soft_delete_picture(db: Session, tsClient: Client, picture_pk, labbook_data, user):
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

    # First possibility
    if user.admin:
        try:
            db.commit()
        except SQLAlchemyError as e:
            logger.error(e)
            db.close()
            return pic_to_update
        db.refresh(pic_to_update)

        db_user_created = db.query(models.User).get(pic_to_update.created_by_id)
        pic_to_update.created_by = db_user_created
        pic_to_update.last_modified_by = user

        query = db.query(models.Labbookchildelement).filter_by(
            labbook_id=labbook_data.labbook_pk, deleted=False).all()

        if not query:
            try:
                transmit(
                    {'model_name': 'labbook',
                     'model_pk': labbook_data.labbook_pk})
            except RuntimeError as e:
                logger.error(e)

        create_history_entry(db=db,
                             elem_id=picture_pk,
                             user=user,
                             object_type_id=40,
                             changeset_type='S',
                             changerecords=[])
        update_delete_status_typesense(pic_to_update, True, tsClient)
        return pic_to_update

    if not user.admin and lb_to_update.strict_mode \
            and user.id != pic_to_update.created_by_id:
        return None

    # Second possibility: it's a picture created by admin
    if check_for_admin_role_with_user_id(db=db,
                                         user_id=pic_to_update.created_by_id):

        # allowed only for groupadmins
        if check_for_labbook_admin_access(db=db, labbook_pk=lb_elem.labbook_id,
                                          user=user):
            try:
                db.commit()
            except SQLAlchemyError as e:
                logger.error(e)
                db.close()
                return pic_to_update
            db.refresh(pic_to_update)

            db_user_created = db.query(models.User).get(
                pic_to_update.created_by_id)
            pic_to_update.created_by = db_user_created
            pic_to_update.last_modified_by = user

            query = db.query(models.Labbookchildelement).filter_by(
                labbook_id=labbook_data.labbook_pk, deleted=False).all()

            if not query:
                try:
                    transmit(
                        {'model_name': 'labbook',
                         'model_pk': labbook_data.labbook_pk})
                except RuntimeError as e:
                    logger.error(e)

            create_history_entry(db=db,
                                 elem_id=picture_pk,
                                 user=user,
                                 object_type_id=40,
                                 changeset_type='S',
                                 changerecords=[])
            update_delete_status_typesense(pic_to_update, True, tsClient)
            return pic_to_update
        else:
            return None

    if check_for_guest_role(db=db, labbook_pk=lb_elem.labbook_id, user=user):
        return None

    # Third possibility: it's a note created by user
    labbook_ids = get_all_labbook_ids_from_non_admin_user(db=db, user=user)

    if lb_elem.labbook_id in labbook_ids:
        try:
            db.commit()
        except SQLAlchemyError as e:
            logger.error(e)
            db.close()
            return pic_to_update
        db.refresh(pic_to_update)

        db_user_created = db.query(models.User).get(
            pic_to_update.created_by_id)
        pic_to_update.created_by = db_user_created
        pic_to_update.last_modified_by = user

        query = db.query(models.Labbookchildelement).filter_by(
            labbook_id=labbook_data.labbook_pk, deleted=False).all()

        if not query:
            try:
                transmit(
                    {'model_name': 'labbook',
                     'model_pk': labbook_data.labbook_pk})
            except RuntimeError as e:
                logger.error(e)

        create_history_entry(db=db,
                             elem_id=picture_pk,
                             user=user,
                             object_type_id=40,
                             changeset_type='S',
                             changerecords=[])

        update_delete_status_typesense(pic_to_update, True, tsClient)
        return pic_to_update

    return None


def restore_picture(db: Session, tsClient: Client, picture_pk, user):
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

    # First possibility
    if user.admin:
        try:
            db.commit()
        except SQLAlchemyError as e:
            logger.error(e)
            db.close()
            return pic_to_update
        db.refresh(pic_to_update)

        db_user_created = db.query(models.User).get(pic_to_update.created_by_id)
        pic_to_update.created_by = db_user_created
        pic_to_update.last_modified_by = user

        query = db.query(models.Labbookchildelement).filter_by(
            labbook_id=lb_elem.labbook_id, deleted=False).all()

        if not query:
            try:
                transmit(
                    {'model_name': 'labbook',
                     'model_pk': lb_elem.labbook_id})
            except RuntimeError as e:
                logger.error(e)

        create_history_entry(db=db,
                             elem_id=picture_pk,
                             user=user,
                             object_type_id=40,
                             changeset_type='R',
                             changerecords=[])
        update_delete_status_typesense(pic_to_update, False, tsClient)
        return pic_to_update

    # Second possibility: it's a note created by admin
    if check_for_admin_role_with_user_id(db=db,
                                         user_id=pic_to_update.created_by_id):

        # allowed only for groupadmins
        if check_for_labbook_admin_access(db=db, labbook_pk=lb_elem.labbook_id,
                                          user=user):
            try:
                db.commit()
            except SQLAlchemyError as e:
                logger.error(e)
                db.close()
                return pic_to_update
            db.refresh(pic_to_update)

            db_user_created = db.query(models.User).get(
                pic_to_update.created_by_id)
            pic_to_update.created_by = db_user_created
            pic_to_update.last_modified_by = user

            query = db.query(models.Labbookchildelement).filter_by(
                labbook_id=lb_elem.labbook_id, deleted=False).all()

            if not query:
                try:
                    transmit(
                        {'model_name': 'labbook',
                         'model_pk': lb_elem.labbook_id})
                except RuntimeError as e:
                    logger.error(e)
            create_history_entry(db=db,
                                 elem_id=picture_pk,
                                 user=user,
                                 object_type_id=40,
                                 changeset_type='R',
                                 changerecords=[])
            update_delete_status_typesense(pic_to_update, False, tsClient)
            return pic_to_update
        else:
            return None

    if check_for_guest_role(db=db, labbook_pk=lb_elem.labbook_id, user=user):
        return None
    # Third possibility: it's a note created by user
    labbook_ids = get_all_labbook_ids_from_non_admin_user(db=db, user=user)

    if lb_elem.labbook_id in labbook_ids:
        try:
            db.commit()
        except SQLAlchemyError as e:
            logger.error(e)
            db.close()
            return pic_to_update
        db.refresh(pic_to_update)

        db_user_created = db.query(models.User).get(
            pic_to_update.created_by_id)
        pic_to_update.created_by = db_user_created
        pic_to_update.last_modified_by = user

        query = db.query(models.Labbookchildelement).filter_by(
            labbook_id=lb_elem.labbook_id, deleted=False).all()

        if not query:
            try:
                transmit(
                    {'model_name': 'labbook',
                     'model_pk': lb_elem.labbook_id})
            except RuntimeError as e:
                logger.error(e)

        create_history_entry(db=db,
                             elem_id=picture_pk,
                             user=user,
                             object_type_id=40,
                             changeset_type='R',
                             changerecords=[])
        update_delete_status_typesense(pic_to_update, False, tsClient)
        return pic_to_update

    return None


def remove_soft_deleted_picture(db: Session, picture_pk):
    pic_to_remove = db.query(models.Picture).get(picture_pk)

    bi_img_path = f'{PICTURES_BASE_PATH}{pic_to_remove.background_image}'

    if pic_to_remove and pic_to_remove.deleted:
        lb_elem = db.query(models.Labbookchildelement).get(
            pic_to_remove.elem_id)
        # only comment relations
        relations = db.query(models.Relation).filter_by(
            right_object_id=picture_pk, left_content_type=70).all()
        db.delete(pic_to_remove)
        # it has to be committed first because of foreign key dependency lb_elem
        try:
            db.commit()
        except SQLAlchemyError as e:
            print(e)
            db.close()
            return

        db.delete(lb_elem)
        for relation in relations:
            db.delete(relation)

        try:
            db.commit()
        except SQLAlchemyError as e:
            print(e)
            db.close()
            return
        try:
            file_to_rem = pathlib.Path(bi_img_path)
            file_to_rem.unlink()
        except FileNotFoundError as e:
            print(e)
            return
        return True
    return


def get_canvas_content_with_imgbase64(img_src: str, canvas_width=950,
                                      canvas_height=712):
    w, h = get_image_size_from_base64(img_src)

    obj = {
        "version": "6.9.0",
        "objects": [
            {
                "type": "Image",
                "version": "6.9.1",
                "originX": "center",
                "originY": "center",
                "left": canvas_width / 2,
                "top": canvas_height / 2,
                "width": w,
                "height": h,
                "scaleX": 1,
                "scaleY": 1,
                "angle": 0,
                "src": f"data:image/png;base64,{img_src}",
                "crossOrigin": "anonymous",
                "filters": []
            }
        ],
        "background": "#F8F8FF"
    }

    return json.dumps(obj)


def get_image_size_from_base64(img_base64: str):
    # strip header if present
    if img_base64.startswith("data:image"):
        img_base64 = img_base64.split(",")[1]

    img_bytes = base64.b64decode(img_base64)
    img = Image.open(io.BytesIO(img_bytes))

    return img.width, img.height
