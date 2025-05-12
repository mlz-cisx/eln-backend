from sqlalchemy.orm import Session, aliased
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select, func, and_, or_

import datetime

from typesense.client import Client
from typesense.exceptions import TypesenseClientError
from joeseln_backend.full_text_search.html_stripper import strip_html_and_binary

from joeseln_backend.models import models
from joeseln_backend.services.labbookchildelements.labbookchildelement_schemas import *

from joeseln_backend.ws.ws_client import transmit
from joeseln_backend.services.picture import picture_service
from joeseln_backend.services.file import file_service

from joeseln_backend.services.labbook.labbook_service import \
    check_for_labbook_access, get_all_labbook_ids_from_non_admin_user, \
    check_for_labbook_admin_access

from joeseln_backend.services.note.note_service import get_note_relations, \
    get_note_related_comments_count, get_note

from joeseln_backend.services.file.file_service import get_file_relations, \
    get_file_related_comments_count

from joeseln_backend.services.picture.picture_service import \
    get_picture_relations, \
    get_picture_related_comments_count

from joeseln_backend.auth import security

from joeseln_backend.mylogging.root_logger import logger

from joeseln_backend.conf.base_conf import URL_BASE_PATH


def map_to_child_object_model(child_object_content_type):
    if child_object_content_type == 30:
        return 'shared_elements.note'
    if child_object_content_type == 40:
        return 'pictures.picture'
    if child_object_content_type == 50:
        return 'shared_elements.file'


def get_lb_childelements_for_export(db: Session, labbook_pk, access_token, user,
                                    as_export):
    query = db.query(models.Labbookchildelement).filter_by(
        labbook_id=labbook_pk, deleted=False).order_by(
        models.Labbookchildelement.position_y).all()

    for elem in query:
        if elem.child_object_content_type == 30:
            elem.child_object = get_note(db=db, note_pk=elem.child_object_id)
            elem.relations = get_note_relations(db=db,
                                                note_pk=elem.child_object_id,
                                                params='',
                                                user=user)

        if elem.child_object_content_type == 40:
            elem.child_object = picture_service.get_picture_in_lb_init(db=db,
                                                                       picture_pk=elem.child_object_id,
                                                                       access_token=access_token,
                                                                       as_export=as_export)

            elem.relations = get_picture_relations(db=db,
                                                   picture_pk=elem.child_object_id,
                                                   params='',
                                                   user=user)

        if elem.child_object_content_type == 50:
            elem.child_object = file_service.get_file(db=db,
                                                      file_pk=elem.child_object_id,
                                                      user=user)

            elem.relations = get_file_relations(db=db,
                                                file_pk=elem.child_object_id,
                                                params='', user=user)

    return query


def get_lb_childelements_for_zip_export(db: Session, labbook_pk, user,
                                        as_export):
    query = db.query(models.Labbookchildelement).filter_by(
        labbook_id=labbook_pk, deleted=False).order_by(
        models.Labbookchildelement.position_y).all()

    for elem in query:
        if elem.child_object_content_type == 30:
            elem.child_object = db.query(models.Note).get(elem.child_object_id)
            elem.relations = get_note_relations(db=db,
                                                note_pk=elem.child_object_id,
                                                params='',
                                                user=user)

        if elem.child_object_content_type == 40:
            elem.child_object = picture_service.get_picture_for_zip_export(
                db=db,
                picture_pk=elem.child_object_id)

            elem.relations = get_picture_relations(db=db,
                                                   picture_pk=elem.child_object_id,
                                                   params='',
                                                   user=user)

        if elem.child_object_content_type == 50:
            elem.child_object = file_service.get_file_for_zip_export(db=db,
                                                                     file_pk=elem.child_object_id,
                                                                     user=user)

            elem.relations = get_file_relations(db=db,
                                                file_pk=elem.child_object_id,
                                                params='', user=user)

    return query


def get_lb_childelements_from_user(db: Session, labbook_pk, as_export, user):
    if not check_for_labbook_access(db=db, labbook_pk=labbook_pk, user=user):
        return None

    access_token = security.build_download_token(user)
    jwt = security.Token(access_token=access_token, token_type="bearer").access_token

    created_by = aliased(models.User)
    last_modified_by = aliased(models.User)

    # subquery to get comment count
    related_comments_count = (
        select(func.count())
        .where(
            and_(
                models.Relation.right_object_id == models.Labbookchildelement.child_object_id,
                models.Relation.left_content_type == 70,
                models.Relation.deleted == False,
            )
        )
    ).correlate(models.Labbookchildelement).scalar_subquery()

    # note query
    query = (
        select(
            models.Labbookchildelement,
            models.Note,
            created_by,
            last_modified_by,
            related_comments_count.label('num_related_comments')
        )
        .join(models.Note, models.Labbookchildelement.child_object_id == models.Note.id)
        .join(created_by, models.Note.created_by_id == created_by.id)
        .join(last_modified_by, models.Note.last_modified_by_id == last_modified_by.id)
        .where(
            and_(
                models.Labbookchildelement.labbook_id == labbook_pk,
                models.Labbookchildelement.deleted == False,
                models.Labbookchildelement.child_object_content_type == 30
            )
        )
    )
    results = db.execute(query).fetchall()

    notes = [
        {
            **item[0].__dict__,
            'child_object': {**item[1].__dict__, 
                             'created_by': item[2], 
                             'last_modified_by': item[3]},
            'num_related_comments': item[4]
        }
        for item in results
    ]

    # picture query
    query = (
        select(
            models.Labbookchildelement,
            models.Picture,
            created_by,
            last_modified_by,
            related_comments_count.label('num_related_comments')
        )
        .join(models.Picture, models.Labbookchildelement.child_object_id == models.Picture.id)
        .join(created_by, models.Picture.created_by_id == created_by.id)
        .join(last_modified_by, models.Picture.last_modified_by_id == last_modified_by.id)
        .where(
            and_(
                models.Labbookchildelement.labbook_id == labbook_pk,
                models.Labbookchildelement.deleted == False,
                models.Labbookchildelement.child_object_content_type == 40
            )
        )
    )
    results = db.execute(query).fetchall()

    pictures = [
        {
            **item[0].__dict__,
            'child_object': {**item[1].__dict__,
                             'created_by': item[2], 
                             'last_modified_by': item[3],
                             'background_image': f'{URL_BASE_PATH}pictures/{item[1].id}/bi_download/?jwt={jwt}',
                             'rendered_image': f'{URL_BASE_PATH}pictures/{item[1].id}/ri_download/?jwt={jwt}',
                             'shapes_image': f'{URL_BASE_PATH}pictures/{item[1].id}/shapes/?jwt={jwt}'
                            },
            'num_related_comments': item[4]
        }
        for item in results
    ]

    # file query
    query = (
        select(
            models.Labbookchildelement,
            models.File,
            created_by,
            last_modified_by,
            related_comments_count.label('num_related_comments')
        )
        .join(models.File, models.Labbookchildelement.child_object_id == models.File.id)
        .join(created_by, models.File.created_by_id == created_by.id)
        .join(last_modified_by, models.File.last_modified_by_id == last_modified_by.id)
        .where(
            and_(
                models.Labbookchildelement.labbook_id == labbook_pk,
                models.Labbookchildelement.deleted == False,
                models.Labbookchildelement.child_object_content_type == 50
            )
        )
    )
    results = db.execute(query).fetchall()

    files = [
        {
            **item[0].__dict__,
            'child_object': {**item[1].__dict__,
                             'created_by': item[2], 
                             'last_modified_by': item[3],
                             'path': f'{URL_BASE_PATH}files/{item[1].id}/download?jwt={jwt}'
                            },
            'num_related_comments': item[4]
        }
        for item in results
    ]

    elems= notes + pictures + files
    elems = sorted(elems, key=lambda elem: elem['position_y'])
    return elems


def check_for_version_edit_access_on_lb_elem(db: Session, lb_elem, user):
    elem_creator = db.query(models.User).get(lb_elem.created_by_id)
    # lowest rights
    if not elem_creator.admin:
        return True
    else:
        return check_for_labbook_admin_access(db=db,
                                              labbook_pk=lb_elem.labbook_id,
                                              user=user)


def patch_lb_childelement(db: Session, labbook_pk, element_pk,
                          labbook_childelem, user):
    if not check_for_labbook_access(db=db, labbook_pk=labbook_pk, user=user):
        return None

    db_labbook_elem = db.query(models.Labbookchildelement).get(element_pk)
    db_labbook_elem.position_x = labbook_childelem.position_x
    db_labbook_elem.position_y = labbook_childelem.position_y
    db_labbook_elem.width = labbook_childelem.width
    db_labbook_elem.height = labbook_childelem.height
    db_labbook_elem.last_modified_at = datetime.datetime.now()
    db_labbook_elem.last_modified_by_id = user.id

    lb_to_update = db.query(models.Labbook).get(db_labbook_elem.labbook_id)
    lb_to_update.last_modified_at = datetime.datetime.now()
    lb_to_update.last_modified_by_id = user.id

    try:
        db.commit()
    except SQLAlchemyError as e:
        logger.error(e)
        db.close()
        return db_labbook_elem

    db.refresh(db_labbook_elem)

    if db_labbook_elem.child_object_content_type == 30:
        db_labbook_elem.child_object = get_note(db=db,
                                                note_pk=db_labbook_elem.child_object_id)
        db_labbook_elem.num_related_comments = get_note_related_comments_count(
            db=db,
            note_pk=db_labbook_elem.child_object_id, user=user)
    if db_labbook_elem.child_object_content_type == 40:
        db_labbook_elem.child_object = picture_service.get_picture(db=db,
                                                                   picture_pk=db_labbook_elem.child_object_id,
                                                                   user=user)
        db_labbook_elem.num_related_comments = get_picture_related_comments_count(
            db=db, picture_pk=db_labbook_elem.child_object_id, user=user)

    if db_labbook_elem.child_object_content_type == 50:
        db_labbook_elem.child_object = file_service.get_file(db=db,
                                                             file_pk=db_labbook_elem.child_object_id,
                                                             user=user)
        db_labbook_elem.num_related_comments = get_file_related_comments_count(
            db=db,
            file_pk=db_labbook_elem.child_object_id, user=user)

    return db_labbook_elem


def create_lb_childelement(db: Session, labbook_pk,
                           labbook_childelem: Labbookchildelement_Create, user, typesense: Client):
    if not check_for_labbook_access(db=db, labbook_pk=labbook_pk, user=user):
        return None

    db_labbook_elem = models.Labbookchildelement(
        labbook_id=labbook_pk,
        position_x=labbook_childelem.position_x,
        position_y=labbook_childelem.position_y,
        width=labbook_childelem.width,
        height=labbook_childelem.height,
        child_object_id=labbook_childelem.child_object_id,
        child_object_content_type=labbook_childelem.child_object_content_type,
        child_object_content_type_model=map_to_child_object_model(
            child_object_content_type=labbook_childelem.child_object_content_type),
        version_number=0,
        created_at=datetime.datetime.now(),
        created_by_id=user.id,
        last_modified_at=datetime.datetime.now(),
        last_modified_by_id=user.id
    )
    db.add(db_labbook_elem)

    lb_to_update = db.query(models.Labbook).get(labbook_pk)
    lb_to_update.last_modified_at = datetime.datetime.now()
    lb_to_update.last_modified_by_id = user.id

    try:
        db.commit()
    except SQLAlchemyError as e:
        logger.error(e)
        db.close()
        return db_labbook_elem

    update_child_element(db_labbook_elem=db_labbook_elem,
                         child_object_content_type=db_labbook_elem.child_object_content_type,
                         child_object_id=db_labbook_elem.child_object_id,
                         db=db)

    db.refresh(db_labbook_elem)

    if db_labbook_elem.child_object_content_type == 30:
        note = get_note(db=db, note_pk=db_labbook_elem.child_object_id)
        db_labbook_elem.child_object = note
        db_labbook_elem.num_related_comments = get_note_related_comments_count(
            db=db,
            note_pk=db_labbook_elem.child_object_id, user=user)
        try:
            # insert note to typesense for searching purpose
            stripped_content = strip_html_and_binary(note.content)
            typesense.collections['notes'].documents.upsert({'id': str(note.id),
                                                            'elem_id': str(db_labbook_elem.id),
                                                            'subject': note.subject, 
                                                            'content': stripped_content, 
                                                            'last_modified_at': int(note.last_modified_at.timestamp()),
                                                            'labbook_id': str(labbook_pk),
                                                            'soft_delete': False})
        except TypesenseClientError as e:
            logger.error(e)

    if db_labbook_elem.child_object_content_type == 40:
        db_labbook_elem.child_object = picture_service.get_picture(db=db,
                                                                   picture_pk=db_labbook_elem.child_object_id,
                                                                   user=user)
        db_labbook_elem.num_related_comments = get_picture_related_comments_count(
            db=db, picture_pk=db_labbook_elem.child_object_id, user=user)

    if db_labbook_elem.child_object_content_type == 50:
        db_labbook_elem.child_object = file_service.get_file(db=db,
                                                             file_pk=db_labbook_elem.child_object_id,
                                                             user=user)
        db_labbook_elem.num_related_comments = get_file_related_comments_count(
            db=db,
            file_pk=db_labbook_elem.child_object_id, user=user)

    try:
        transmit({'model_name': 'labbook', 'model_pk': str(labbook_pk)})
    except RuntimeError as e:
        logger.error(e)

    return db_labbook_elem


def update_all_lb_childelements(db: Session,
                                labbook_childelems, labbook_pk, user):
    if not check_for_labbook_access(db=db, labbook_pk=labbook_pk, user=user):
        return

    now = datetime.datetime.now()
    update_data = [{
        'id': lb_childelem.id,
        'position_x': lb_childelem.position_x,
        'position_y': lb_childelem.position_y,
        'width': lb_childelem.width,
        'height': lb_childelem.height,
        'last_modified_at': now,
        'last_modified_by_id': user.id
    } for lb_childelem in labbook_childelems]

    db.bulk_update_mappings(models.Labbookchildelement, update_data)

    try:
        db.commit()
    except SQLAlchemyError as e:
        logger.error(e)
        db.close()
        return

    transmit({'model_name': 'labbook', 'model_pk': str(labbook_pk)})

    return True


def update_child_element(db_labbook_elem, child_object_content_type,
                         child_object_id, db):
    if child_object_content_type == 30:
        note = db.query(models.Note).get(child_object_id)
        note.elem_id = db_labbook_elem.id
        try:
            db.commit()
        except SQLAlchemyError as e:
            logger.error(e)
            db.close()

    if child_object_content_type == 40:
        picture = db.query(models.Picture).get(child_object_id)
        picture.elem_id = db_labbook_elem.id
        try:
            db.commit()
        except SQLAlchemyError as e:
            logger.error(e)
            db.close()

    if child_object_content_type == 50:
        file = db.query(models.File).get(child_object_id)
        file.elem_id = db_labbook_elem.id
        try:
            db.commit()
        except SQLAlchemyError as e:
            logger.error(e)
            db.close()
