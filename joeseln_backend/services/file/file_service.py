import pathlib
import sys
from copy import deepcopy

from fastapi.responses import FileResponse
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from joeseln_backend.auth.security import get_user_from_jwt
from joeseln_backend.services.entry_path.entry_path_service import create_path, \
    create_entry
from joeseln_backend.auth import security
from joeseln_backend.models import models
from joeseln_backend.services.file.file_schemas import *
from joeseln_backend.services.history.history_service import \
    create_history_entry, create_file_update_history_entry
from joeseln_backend.services.labbook.labbook_service import \
    check_for_labbook_access, get_all_labbook_ids_from_non_admin_user, \
    check_for_labbook_admin_access
from joeseln_backend.services.privileges.admin_privileges.privileges_service import \
    ADMIN
from joeseln_backend.services.privileges.privileges_service import \
    create_file_privileges, create_strict_privileges
from joeseln_backend.services.user_to_group.user_to_group_service import \
    get_user_group_roles_with_match, get_user_group_roles, \
    check_for_admin_role_with_user_id, check_for_guest_role
from joeseln_backend.ws.ws_client import transmit
from joeseln_backend.helper import db_ordering
from joeseln_backend.conf.base_conf import FILES_BASE_PATH, URL_BASE_PATH, \
    LABBOOK_QUERY_MODE, ELEM_MAXIMUM_SIZE
from joeseln_backend.services.comment.comment_schemas import Comment

from joeseln_backend.mylogging.root_logger import logger


def get_all_files(db: Session, params, user):
    # print(params.get('ordering'))
    order_params = db_ordering.get_order_params(ordering=params.get('ordering'))

    if user.admin:
        if params.get('search'):
            search_text = params.get('search')
            files = db.query(models.File).filter_by(
                deleted=bool(params.get('deleted'))).join(
                models.Labbookchildelement,
                models.File.elem_id ==
                models.Labbookchildelement.id).join(models.Labbook,
                                                    models.Labbook.id ==
                                                    models.Labbookchildelement.labbook_id). \
                filter(or_
                       (models.Labbook.title.ilike(f'%{search_text}%'),
                        models.File.title.ilike(f'%{search_text}%'))).order_by(
                text('file.' + order_params)).offset(
                params.get('offset')).limit(
                params.get('limit')).all()
        else:
            files = db.query(models.File).filter_by(
                deleted=bool(params.get('deleted'))).order_by(
                text(order_params)).offset(params.get('offset')).limit(
                params.get('limit')).all()
        for file in files:
            db_user_created = db.query(models.User).get(file.created_by_id)
            db_user_modified = db.query(models.User).get(
                file.last_modified_by_id)
            file.created_by = db_user_created
            file.last_modified_by = db_user_modified

            try:
                lb_elem = db.query(models.Labbookchildelement).get(file.elem_id)
                lb = db.query(models.Labbook).get(lb_elem.labbook_id)
                file.lb_title = lb.title
            except:
                file.lb_title = 'None'

        return files

    labbook_ids = get_all_labbook_ids_from_non_admin_user(db=db, user=user)

    if params.get('search'):
        search_text = params.get('search')
        files = db.query(models.File).filter_by(
            deleted=bool(params.get('deleted'))). \
            join(models.Labbookchildelement,
                 models.File.elem_id ==
                 models.Labbookchildelement.id).filter(
            models.Labbookchildelement.labbook_id.in_(labbook_ids)).join(
            models.Labbook,
            models.Labbook.id ==
            models.Labbookchildelement.labbook_id). \
            filter(or_
                   (models.Labbook.title.ilike(f'%{search_text}%'),
                    models.File.title.ilike(f'%{search_text}%'))).order_by(
            text('file.' + order_params)).offset(
            params.get('offset')).limit(
            params.get('limit')).all()
    else:
        files = db.query(models.File).filter_by(
            deleted=bool(params.get('deleted'))). \
            join(models.Labbookchildelement,
                 models.File.elem_id ==
                 models.Labbookchildelement.id).filter(
            models.Labbookchildelement.labbook_id.in_(labbook_ids)).order_by(
            text('file.' + order_params)).offset(
            params.get('offset')).limit(
            params.get('limit')).all()

    for file in files:
        db_user_created = db.query(models.User).get(file.created_by_id)
        db_user_modified = db.query(models.User).get(
            file.last_modified_by_id)
        file.created_by = db_user_created
        file.last_modified_by = db_user_modified
        try:
            lb_elem = db.query(models.Labbookchildelement).get(file.elem_id)
            lb = db.query(models.Labbook).get(lb_elem.labbook_id)
            file.lb_title = lb.title
        except:
            file.lb_title = 'None'

    return files


def get_file(db: Session, file_pk, user):
    db_file = db.query(models.File).get(file_pk)
    db_user_created = db.query(models.User).get(db_file.created_by_id)
    db_user_modified = db.query(models.User).get(db_file.last_modified_by_id)

    file_content = build_download_url_with_token(
        file_to_process=deepcopy(db_file),
        user=user)
    file_content.created_by = db_user_created
    file_content.last_modified_by = db_user_modified

    return file_content


def get_all_deleted_files(db: Session):
    files = db.query(models.File).filter_by(
        deleted=True).order_by(text('display asc')).all()
    return files


def get_file_with_privileges(db: Session, file_pk, user):
    db_file = db.query(models.File).get(file_pk)
    if db_file:
        db_user_created = db.query(models.User).get(db_file.created_by_id)
        db_user_modified = db.query(models.User).get(
            db_file.last_modified_by_id)

        file_content = build_download_url_with_token(
            file_to_process=deepcopy(db_file),
            user=user)
        file_content.created_by = db_user_created
        file_content.last_modified_by = db_user_modified

        lb_elem = db.query(models.Labbookchildelement).get(db_file.elem_id)

        if not lb_elem:
            return None

        file_content.position_y = lb_elem.position_y
        file_content.labbook_id = lb_elem.labbook_id

        if user.admin:
            return {'privileges': ADMIN,
                    'file': file_content}

        if not check_for_labbook_access(db=db, labbook_pk=lb_elem.labbook_id,
                                        user=user):
            return None

        db_lb = db.query(models.Labbook).get(lb_elem.labbook_id)
        db_user = db.query(models.User).get(db_file.created_by_id)

        file_created_by = 'USER'
        if db_user.admin:
            file_created_by = 'ADMIN'

        if db_lb and not db_lb.strict_mode:
            if LABBOOK_QUERY_MODE == 'match':
                user_roles = get_user_group_roles_with_match(db=db,
                                                             username=user.username,
                                                             groupname=db_lb.title)
                privileges = create_file_privileges(created_by=file_created_by,
                                                    user_roles=user_roles)

            else:
                user_roles = get_user_group_roles(db=db,
                                                  username=user.username,
                                                  groupname=db_lb.title)
                privileges = create_file_privileges(created_by=file_created_by,
                                                    user_roles=user_roles)

            return {'privileges': privileges, 'file': file_content}

        if db_lb and db_lb.strict_mode and user.id == db_user.id:
            privileges = create_strict_privileges(
                created_by='SELF')
            return {'privileges': privileges, 'file': file_content}

        if db_lb and db_lb.strict_mode and user.id != db_user.id:
            privileges = create_strict_privileges(
                created_by='ANOTHER')
            return {'privileges': privileges, 'file': file_content}

        return None
    return None


def get_file_relations(db: Session, file_pk, params, user):
    db_file = db.query(models.File).get(file_pk)
    lb_elem = db.query(models.Labbookchildelement).get(db_file.elem_id)
    if check_for_labbook_access(db=db, labbook_pk=lb_elem.labbook_id,
                                user=user):
        if not params:
            relations = db.query(models.Relation).filter_by(
                right_object_id=file_pk, deleted=False).order_by(
                models.Relation.created_at).all()
        else:
            order_params = db_ordering.get_order_params(
                ordering=params.get('ordering'))

            relations = db.query(models.Relation).filter_by(
                right_object_id=file_pk, deleted=False).order_by(
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

            db_file = db.query(models.File).get(file_pk)
            db_user_created = db.query(models.User).get(db_file.created_by_id)
            db_user_modified = db.query(models.User).get(
                db_file.last_modified_by_id)
            db_file.created_by = db_user_created
            db_file.last_modified_by = db_user_modified
            rel.right_content_object = db_file

        return relations
    return []


def delete_file_relation(db: Session, file_pk, relation_pk, user):
    db_file = db.query(models.File).get(file_pk)
    lb_elem = db.query(models.Labbookchildelement).get(db_file.elem_id)
    if check_for_labbook_access(db=db, labbook_pk=lb_elem.labbook_id,
                                user=user):
        db_relation = db.query(models.Relation).get(relation_pk)
        db_relation.deleted = True
        try:
            db.commit()
        except SQLAlchemyError as e:
            logger.error(e)
            db.close()
            return
        db.refresh(db_relation)

        return get_file_relations(db=db, file_pk=file_pk, params='', user=user)
    return None


def get_file_related_comments_count(db: Session, file_pk, user):
    # user authorization is done in the elements
    relations_count = db.query(models.Relation).filter_by(
        right_object_id=file_pk, deleted=False, left_content_type=70).count()

    return relations_count


def get_lb_pk_from_file(db: Session, file_pk):
    file = db.query(models.File).get(file_pk)
    elem = db.query(models.Labbookchildelement).get(file.elem_id)
    return elem.labbook_id


def create_file(db: Session, title: str,
                name: str, file_size: int, description: str, mime_type: str,
                user):
    if file_size > ELEM_MAXIMUM_SIZE << 10 or sys.getsizeof(
            description) > ELEM_MAXIMUM_SIZE << 10:
        return

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
                          created_by_id=user.id,
                          last_modified_at=datetime.datetime.now(),
                          last_modified_by_id=user.id)

    db.add(db_file)
    try:
        db.commit()
    except SQLAlchemyError as e:
        logger.error(e)
        db.close()
        return
    db.refresh(db_file)

    # changerecord = [field_name,old_value,new_value]
    # changerecords = [changerecord, changerecord, .....]
    changerecords = [['title', None, title],
                     ['name', None, name]]
    # changeset_types:
    # U : edited/updated, R : restored, S: trashed , I initialized/created
    create_history_entry(db=db,
                         elem_id=db_file.id,
                         user=user,
                         object_type_id=50,
                         changeset_type='I',
                         changerecords=changerecords)

    return db_file


def update_file(file_pk, db: Session, elem: FilePatch, user):
    if sys.getsizeof(elem.description) > ELEM_MAXIMUM_SIZE << 10:
        return None

    db_file = db.query(models.File).get(file_pk)
    old_title = db_file.title
    db_file.title = elem.title
    old_description = db_file.description
    db_file.description = elem.description
    db_file.last_modified_at = datetime.datetime.now()
    db_file.last_modified_by_id = user.id

    lb_elem = db.query(models.Labbookchildelement).get(db_file.elem_id)
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
            db_user_created = db.query(models.User).get(db_file.created_by_id)
            db_file.created_by = db_user_created
            db_file.last_modified_by = user

            db.close()
            return db_file

        db.refresh(db_file)
        transmit({'model_name': 'file', 'model_pk': str(file_pk)})

        db_user_created = db.query(models.User).get(db_file.created_by_id)
        db_file.created_by = db_user_created
        db_file.last_modified_by = user

        # changerecord = [field_name,old_value,new_value]
        # changerecords = [changerecord, changerecord, .....]
        if old_description == elem.description:
            changerecords = [['title', old_title, elem.title]]
        else:
            changerecords = [['title', old_title, elem.title],
                             ['description', old_description, elem.description]]
        # changeset_types:
        # U : edited/updated, R : restored, S: trashed , I initialized/created
        create_file_update_history_entry(db=db,
                                         elem_id=db_file.id,
                                         user=user,
                                         object_type_id=50,
                                         changeset_type='U',
                                         changerecords=changerecords)

        return db_file

    # Second possibility: file is created by admin und user is now not admin
    if check_for_admin_role_with_user_id(db=db,
                                         user_id=db_file.created_by_id):
        return None

    if lb_to_update.strict_mode and user.id != db_file.created_by_id:
        return None

    if check_for_guest_role(db=db, labbook_pk=lb_elem.labbook_id, user=user):
        return None

    labbook_ids = get_all_labbook_ids_from_non_admin_user(db=db, user=user)

    # Third possibility: consider a file created by non admin
    if lb_elem.labbook_id in labbook_ids:
        try:
            db.commit()
        except SQLAlchemyError as e:
            logger.error(e)

            db_user_created = db.query(models.User).get(db_file.created_by_id)
            db_file.created_by = db_user_created
            db_file.last_modified_by = user

            db.close()

            return db_file

        if old_description == elem.description:
            changerecords = [['title', old_title, elem.title]]
        else:
            changerecords = [['title', old_title, elem.title],
                             ['description', old_description, elem.description]]
        # changeset_types:
        # U : edited/updated, R : restored, S: trashed , I initialized/created
        create_file_update_history_entry(db=db,
                                         elem_id=db_file.id,
                                         user=user,
                                         object_type_id=50,
                                         changeset_type='U',
                                         changerecords=changerecords)

        db.refresh(db_file)
        transmit({'model_name': 'file', 'model_pk': str(file_pk)})

        db_user_created = db.query(models.User).get(db_file.created_by_id)
        db_file.created_by = db_user_created
        db_file.last_modified_by = user

        return db_file

    return None


def process_file_upload_form(form, db, contents, user):
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
                          mime_type=form['path'].content_type,
                          user=user)
    if not db_file:
        return None
    file_path = f'{FILES_BASE_PATH}{db_file.path}'

    with open(file_path, 'wb') as file:
        file.write(contents)
        file.close()

    db.close()

    ret_file = build_download_url_with_token(file_to_process=deepcopy(db_file),
                                             user=user)

    ret_file.created_by = user
    ret_file.last_modified_by = user

    return ret_file


def build_download_url_with_token(file_to_process, user):
    access_token_expires = security.timedelta(
        minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    file_to_process.path = f'{URL_BASE_PATH}files/{file_to_process.id}/download?jwt={security.Token(access_token=access_token, token_type="bearer").access_token}'
    return file_to_process


def build_file_download_response(file_pk, db, jwt):
    user = get_user_from_jwt(token=jwt)
    if user is None:
        return
    db_file = db.query(models.File).get(file_pk)
    file_path = f'{FILES_BASE_PATH}{db_file.path}'
    value = FileResponse(file_path)

    return value


def get_file_export_link(db: Session, file_pk, user):
    db_file = db.query(models.File).get(file_pk)
    db_file = build_file_download_url_with_token(
        file_to_process=db_file,
        user=user)
    export_link = {
        'url': db_file.path,
        'filename': f'{db_file.title}.pdf'
    }

    lb_elem = db.query(models.Labbookchildelement).get(db_file.elem_id)

    if check_for_labbook_access(
            db=db, labbook_pk=lb_elem.labbook_id,
            user=user):
        return export_link

    return None


def build_file_download_url_with_token(file_to_process, user):
    access_token_expires = security.timedelta(
        minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    file_to_process.path = f'{URL_BASE_PATH}files/{file_to_process.id}/export?jwt={security.Token(access_token=access_token, token_type="bearer").access_token}'
    return file_to_process


# needs to be heavily factorized
def soft_delete_file(db: Session, file_pk, labbook_data, user):
    file_to_update = db.query(models.File).get(file_pk)
    file_to_update.deleted = True
    file_to_update.last_modified_at = datetime.datetime.now()
    file_to_update.last_modified_by_id = user.id

    lb_elem = db.query(models.Labbookchildelement).get(file_to_update.elem_id)
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
            db_user_created = db.query(models.User).get(
                file_to_update.created_by_id)
            file_to_update.created_by = db_user_created
            file_to_update.last_modified_by = user

            db.close()
            return file_to_update
        db.refresh(file_to_update)
        query = db.query(models.Labbookchildelement).filter_by(
            labbook_id=labbook_data.labbook_pk, deleted=False).all()
        if not query:
            try:
                transmit(
                    {'model_name': 'labbook',
                     'model_pk': labbook_data.labbook_pk})
            except RuntimeError as e:
                logger.error(e)

        db_user_created = db.query(models.User).get(
            file_to_update.created_by_id)
        file_to_update.created_by = db_user_created
        file_to_update.last_modified_by = user

        create_history_entry(db=db,
                             elem_id=file_pk,
                             user=user,
                             object_type_id=50,
                             changeset_type='S',
                             changerecords=[])
        return file_to_update

    if lb_to_update.strict_mode and user.id != file_to_update.created_by_id:
        return None

    # Second possibility: it's a file created by admin
    if check_for_admin_role_with_user_id(db=db,
                                         user_id=file_to_update.created_by_id):

        # allowed only for groupadmins
        if check_for_labbook_admin_access(db=db, labbook_pk=lb_elem.labbook_id,
                                          user=user):
            try:
                db.commit()
            except SQLAlchemyError as e:
                logger.error(e)
                db_user_created = db.query(models.User).get(
                    file_to_update.created_by_id)
                file_to_update.created_by = db_user_created
                file_to_update.last_modified_by = user
                db.close()
                return file_to_update
            db.refresh(file_to_update)
            query = db.query(models.Labbookchildelement).filter_by(
                labbook_id=labbook_data.labbook_pk, deleted=False).all()
            if not query:
                try:
                    transmit(
                        {'model_name': 'labbook',
                         'model_pk': labbook_data.labbook_pk})
                except RuntimeError as e:
                    logger.error(e)

            db_user_created = db.query(models.User).get(
                file_to_update.created_by_id)
            file_to_update.created_by = db_user_created
            file_to_update.last_modified_by = user
            create_history_entry(db=db,
                                 elem_id=file_pk,
                                 user=user,
                                 object_type_id=50,
                                 changeset_type='S',
                                 changerecords=[])
            return file_to_update
        else:
            return None

    if check_for_guest_role(db=db, labbook_pk=lb_elem.labbook_id, user=user):
        return None

    # Third possibility: it's a file created by user
    labbook_ids = get_all_labbook_ids_from_non_admin_user(db=db, user=user)

    if lb_elem.labbook_id in labbook_ids:
        try:
            db.commit()
        except SQLAlchemyError as e:
            logger.error(e)
            db_user_created = db.query(models.User).get(
                file_to_update.created_by_id)
            file_to_update.created_by = db_user_created
            file_to_update.last_modified_by = user
            db.close()
            return file_to_update
        db.refresh(file_to_update)
        query = db.query(models.Labbookchildelement).filter_by(
            labbook_id=labbook_data.labbook_pk, deleted=False).all()
        if not query:
            try:
                transmit(
                    {'model_name': 'labbook',
                     'model_pk': labbook_data.labbook_pk})
            except RuntimeError as e:
                logger.error(e)

        db_user_created = db.query(models.User).get(
            file_to_update.created_by_id)
        file_to_update.created_by = db_user_created
        file_to_update.last_modified_by = user
        create_history_entry(db=db,
                             elem_id=file_pk,
                             user=user,
                             object_type_id=50,
                             changeset_type='S',
                             changerecords=[])
        return file_to_update

    return None


def restore_file(db: Session, file_pk, user):
    file_to_update = db.query(models.File).get(file_pk)
    file_to_update.deleted = False
    file_to_update.last_modified_at = datetime.datetime.now()
    file_to_update.last_modified_by_id = user.id

    lb_elem = db.query(models.Labbookchildelement).get(file_to_update.elem_id)
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
            db_user_created = db.query(models.User).get(
                file_to_update.created_by_id)
            file_to_update.created_by = db_user_created
            file_to_update.last_modified_by = user

            db.close()
            return file_to_update
        db.refresh(file_to_update)
        query = db.query(models.Labbookchildelement).filter_by(
            labbook_id=lb_elem.labbook_id, deleted=False).all()
        if not query:
            try:
                transmit(
                    {'model_name': 'labbook',
                     'model_pk': lb_elem.labbook_id})
            except RuntimeError as e:
                logger.error(e)

        db_user_created = db.query(models.User).get(
            file_to_update.created_by_id)
        file_to_update.created_by = db_user_created
        file_to_update.last_modified_by = user
        create_history_entry(db=db,
                             elem_id=file_pk,
                             user=user,
                             object_type_id=50,
                             changeset_type='R',
                             changerecords=[])
        return file_to_update

    # Second possibility: it's a file created by admin
    if check_for_admin_role_with_user_id(db=db,
                                         user_id=file_to_update.created_by_id):

        # allowed only for groupadmins
        if check_for_labbook_admin_access(db=db, labbook_pk=lb_elem.labbook_id,
                                          user=user):
            try:
                db.commit()
            except SQLAlchemyError as e:
                logger.error(e)
                db_user_created = db.query(models.User).get(
                    file_to_update.created_by_id)
                file_to_update.created_by = db_user_created
                file_to_update.last_modified_by = user
                db.close()
                return file_to_update
            db.refresh(file_to_update)
            query = db.query(models.Labbookchildelement).filter_by(
                labbook_id=lb_elem.labbook_id, deleted=False).all()
            if not query:
                try:
                    transmit(
                        {'model_name': 'labbook',
                         'model_pk': lb_elem.labbook_id})
                except RuntimeError as e:
                    logger.error(e)

            db_user_created = db.query(models.User).get(
                file_to_update.created_by_id)
            file_to_update.created_by = db_user_created
            file_to_update.last_modified_by = user
            create_history_entry(db=db,
                                 elem_id=file_pk,
                                 user=user,
                                 object_type_id=50,
                                 changeset_type='R',
                                 changerecords=[])
            return file_to_update
        else:
            return None

    if check_for_guest_role(db=db, labbook_pk=lb_elem.labbook_id, user=user):
        return None
    # Third possibility: it's a file created by user
    labbook_ids = get_all_labbook_ids_from_non_admin_user(db=db, user=user)

    if lb_elem.labbook_id in labbook_ids:
        try:
            db.commit()
        except SQLAlchemyError as e:
            logger.error(e)
            db_user_created = db.query(models.User).get(
                file_to_update.created_by_id)
            file_to_update.created_by = db_user_created
            file_to_update.last_modified_by = user
            db.close()
            return file_to_update
        db.refresh(file_to_update)
        query = db.query(models.Labbookchildelement).filter_by(
            labbook_id=lb_elem.labbook_id, deleted=False).all()
        if not query:
            try:
                transmit(
                    {'model_name': 'labbook',
                     'model_pk': lb_elem.labbook_id})
            except RuntimeError as e:
                logger.error(e)

        db_user_created = db.query(models.User).get(
            file_to_update.created_by_id)
        file_to_update.created_by = db_user_created
        file_to_update.last_modified_by = user
        create_history_entry(db=db,
                             elem_id=file_pk,
                             user=user,
                             object_type_id=50,
                             changeset_type='R',
                             changerecords=[])
        return file_to_update

    return None


def remove_soft_deleted_file(db: Session, file_pk):
    file_to_remove = db.query(models.File).get(file_pk)
    file_path = f'{FILES_BASE_PATH}{file_to_remove.path}'

    if file_to_remove and file_to_remove.deleted:
        lb_elem = db.query(models.Labbookchildelement).get(
            file_to_remove.elem_id)
        # only comment relations
        relations = db.query(models.Relation).filter_by(
            right_object_id=file_pk, left_content_type=70).all()
        db.delete(file_to_remove)
        # it has to be committed first because of foreign key dependency lb_elem
        try:
            db.commit()
        except SQLAlchemyError as e:
            print(e)
            db.close()
            return

        try:
            file_to_rem = pathlib.Path(file_path)
            file_to_rem.unlink()
        except FileNotFoundError as e:
            print(e)
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
        return True
    return
