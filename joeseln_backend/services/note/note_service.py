import datetime
import sys

from fastapi.exceptions import HTTPException
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from typesense.client import Client
from typesense.exceptions import TypesenseClientError

from joeseln_backend.auth import security
from joeseln_backend.conf.base_conf import (
    ELEM_MAXIMUM_SIZE,
    LABBOOK_QUERY_MODE,
    URL_BASE_PATH,
)
from joeseln_backend.full_text_search.html_stripper import (
    sanitize_html,
    strip_html_and_binary,
)
from joeseln_backend.helper import db_ordering
from joeseln_backend.models import models
from joeseln_backend.mylogging.root_logger import logger
from joeseln_backend.services.comment.comment_schemas import Comment
from joeseln_backend.services.history.history_service import (
    create_history_entry,
    create_note_update_history_entry,
)
from joeseln_backend.services.labbook.labbook_service import (
    check_for_labbook_access,
    check_for_labbook_admin_access,
    get_all_labbook_ids_from_non_admin_user,
)
from joeseln_backend.services.note.note_schemas import Note, NoteCreate
from joeseln_backend.services.privileges.admin_privileges.privileges_service import (
    ADMIN,
)
from joeseln_backend.services.privileges.privileges_service import (
    create_note_privileges,
    create_strict_privileges,
)
from joeseln_backend.services.user_to_group.user_to_group_service import (
    check_for_admin_role_with_user_id,
    check_for_guest_role,
    get_user_group_roles,
    get_user_group_roles_with_match,
)
from joeseln_backend.ws.ws_client import transmit


def get_all_notes(db: Session, params, user):
    order_params = db_ordering.get_order_params(ordering=params.get('ordering'))

    if user.admin:
        if params.get('search'):
            search_text = params.get('search')
            notes = db.query(models.Note).filter_by(
                deleted=bool(params.get('deleted'))).join(
                models.Labbookchildelement,
                models.Note.elem_id ==
                models.Labbookchildelement.id).join(models.Labbook,
                                                    models.Labbook.id ==
                                                    models.Labbookchildelement.labbook_id). \
                filter(or_
                       (models.Labbook.title.ilike(f'%{search_text}%'),
                        models.Note.subject.ilike(f'%{search_text}%')),
                       models.Labbook.deleted == False). \
                order_by(
                text('note.' + order_params)).offset(
                params.get('offset')).limit(
                params.get('limit')).all()
        else:
            notes = db.query(models.Note).filter_by(
                deleted=bool(params.get('deleted'))).join(
                models.Labbookchildelement,
                models.Note.elem_id ==
                models.Labbookchildelement.id).join(models.Labbook,
                                                    models.Labbook.id ==
                                                    models.Labbookchildelement.labbook_id). \
                filter(models.Labbook.deleted == False).order_by(
                text('note.' + order_params)).offset(
                params.get('offset')).limit(
                params.get('limit')).all()
        for note in notes:
            db_user_created = db.query(models.User).get(note.created_by_id)
            db_user_modified = db.query(models.User).get(
                note.last_modified_by_id)
            note.created_by = db_user_created
            note.last_modified_by = db_user_modified

            try:
                lb_elem = db.query(models.Labbookchildelement).get(note.elem_id)
                lb = db.query(models.Labbook).get(lb_elem.labbook_id)
                note.lb_title = lb.title
            except SQLAlchemyError:
                note.lb_title = 'None'
        return notes

    labbook_ids = get_all_labbook_ids_from_non_admin_user(db=db, user=user)

    if params.get('search'):
        search_text = params.get('search')
        notes = db.query(models.Note).filter_by(
            deleted=bool(params.get('deleted'))). \
            join(models.Labbookchildelement,
                 models.Note.elem_id ==
                 models.Labbookchildelement.id).filter(
            models.Labbookchildelement.labbook_id.in_(labbook_ids)).join(
            models.Labbook,
            models.Labbook.id ==
            models.Labbookchildelement.labbook_id). \
            filter(or_
                   (models.Labbook.title.ilike(f'%{search_text}%'),
                    models.Note.subject.ilike(f'%{search_text}%')),
                   models.Labbook.deleted == False).order_by(
            text('note.' + order_params)).offset(
            params.get('offset')).limit(
            params.get('limit')).all()
    else:
        notes = db.query(models.Note).filter_by(
            deleted=bool(params.get('deleted'))). \
            join(models.Labbookchildelement,
                 models.Note.elem_id ==
                 models.Labbookchildelement.id).join(models.Labbook,
                                                     models.Labbook.id ==
                                                     models.Labbookchildelement.labbook_id).filter(
            models.Labbookchildelement.labbook_id.in_(labbook_ids),
            models.Labbook.deleted == False).order_by(
            text('note.' + order_params)).offset(
            params.get('offset')).limit(
            params.get('limit')).all()

    for note in notes:
        db_user_created = db.query(models.User).get(note.created_by_id)
        db_user_modified = db.query(models.User).get(
            note.last_modified_by_id)
        note.created_by = db_user_created
        note.last_modified_by = db_user_modified

        try:
            lb_elem = db.query(models.Labbookchildelement).get(note.elem_id)
            lb = db.query(models.Labbook).get(lb_elem.labbook_id)
            note.lb_title = lb.title
        except SQLAlchemyError:
            note.lb_title = 'None'

    return notes


def get_note(db: Session, note_pk):
    db_note = db.query(models.Note).get(note_pk)
    db_user_created = db.query(models.User).get(db_note.created_by_id)
    db_user_modified = db.query(models.User).get(db_note.last_modified_by_id)
    db_note.created_by = db_user_created
    db_note.last_modified_by = db_user_modified
    return db_note


def get_note_with_privileges(db: Session, note_pk, user, etag):
    db_note = db.query(models.Note).get(note_pk)
    if db_note:
        if etag == f'{db_note.id}-{db_note.last_modified_at}':
            raise HTTPException(status_code=304)

        db_user_created = db.query(models.User).get(db_note.created_by_id)
        db_user_modified = db.query(models.User).get(
            db_note.last_modified_by_id)
        db_note.created_by = db_user_created
        db_note.last_modified_by = db_user_modified

        lb_elem = db.query(models.Labbookchildelement).get(db_note.elem_id)

        if not lb_elem:
            return None

        if lb_elem:
            db_note.labbook_id = lb_elem.labbook_id
            db_note.position_y = lb_elem.position_y

        if user.admin:
            return {'privileges': ADMIN,
                    'note': db_note}

        if not check_for_labbook_access(db=db, labbook_pk=lb_elem.labbook_id,
                                        user=user):
            return None

        db_lb = db.query(models.Labbook).get(lb_elem.labbook_id)
        db_note_creator = db.query(models.User).get(db_note.created_by_id)

        note_created_by = 'USER'
        if db_note_creator.admin:
            note_created_by = 'ADMIN'

        if db_lb and not db_lb.strict_mode:
            if LABBOOK_QUERY_MODE == 'match':
                user_roles = get_user_group_roles_with_match(db=db,
                                                             username=user.username,
                                                             groupname=db_lb.title)
                privileges = create_note_privileges(created_by=note_created_by,
                                                    user_roles=user_roles)

            else:
                user_roles = get_user_group_roles(db=db,
                                                  username=user.username,
                                                  groupname=db_lb.title)
                privileges = create_note_privileges(created_by=note_created_by,
                                                    user_roles=user_roles)

            return {'privileges': privileges, 'note': db_note}

        if db_lb and db_lb.strict_mode and user.id == db_note_creator.id:
            privileges = create_strict_privileges(
                created_by='SELF')
            return {'privileges': privileges, 'note': db_note}

        if db_lb and db_lb.strict_mode and user.id != db_note_creator.id:
            privileges = create_strict_privileges(
                created_by='ANOTHER')
            return {'privileges': privileges, 'note': db_note}

        return None
    return None


def get_note_relations(db: Session, note_pk, params, user):
    db_note = db.query(models.Note).get(note_pk)
    lb_elem = db.query(models.Labbookchildelement).get(db_note.elem_id)
    if lb_elem:
        if check_for_labbook_access(db=db, labbook_pk=lb_elem.labbook_id,
                                    user=user):
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
                    db_comment = db.query(models.Comment).get(
                        rel.left_object_id)

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
                    db_note.created_by_id)
                db_user_modified = db.query(models.User).get(
                    db_note.last_modified_by_id)
                db_note.created_by = db_user_created
                db_note.last_modified_by = db_user_modified
                rel.right_content_object = db_note

            return relations
        return []
    return []


def delete_note_relation(db: Session, note_pk, relation_pk, user):
    db_note = db.query(models.Note).get(note_pk)
    lb_elem = db.query(models.Labbookchildelement).get(db_note.elem_id)
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

        comments_count = db.query(models.Relation).filter(
            models.Relation.right_object_id == note_pk,
            models.Relation.deleted == False).count()

        transmit({'model_name': 'comments', 'model_pk': str(note_pk),
                  'comments_count': comments_count})

        return get_note_relations(db=db, note_pk=note_pk, params='', user=user)
    return None


def get_note_related_comments_count(db: Session, note_pk, user):
    # TODO should we do this?
    # db_note = db.query(models.Note).get(note_pk)
    # lb_elem = db.query(models.Labbookchildelement).get(db_note.elem_id)
    # if not check_for_labbook_access(db=db, labbook_pk=lb_elem.labbook_id,
    #                             user=user):
    #     relations_count = db.query(models.Relation).filter_by(
    #         right_object_id=note_pk, deleted=False,
    #         left_content_type=70).count()
    #     return relations_count
    # return 0
    relations_count = db.query(models.Relation).filter_by(
        right_object_id=note_pk, deleted=False,
        left_content_type=70).count()
    return relations_count


def create_note(db: Session, note: NoteCreate, user, typesense: Client):
    if sys.getsizeof(note.content) > ELEM_MAXIMUM_SIZE << 10:
        return

    note.content = sanitize_html(note.content)
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

    # changerecord = [field_name,old_value,new_value]
    # changerecords = [changerecord, changerecord, .....]
    changerecords = [['subject', None, note.subject],
                     ['content', None, note.content]]
    # changeset_types:
    # U : edited/updated, R : restored, S: trashed , I initialized/created

    create_history_entry(db=db,
                         elem_id=db_note.id,
                         user=user,
                         object_type_id=30,
                         changeset_type='I',
                         changerecords=changerecords)

    db_note.last_modified_by = user
    db_note.created_by = user

    update_note_typesense(db_note, typesense)

    return db_note

def update_note_typesense(note: Note, typesense: Client):
    stripped_content = strip_html_and_binary(note.content)
    try:
        document = {
                'subject': note.subject, 
                'content': stripped_content, 
                'last_modified_at': int(note.last_modified_at.timestamp())}
        typesense.collections['notes'].documents[str(note.id)].update(document)
    except TypesenseClientError as e:
        logger.error(e)

def update_note(db: Session, note_pk, note: NoteCreate, user, typesense: Client):
    if sys.getsizeof(note.content) > ELEM_MAXIMUM_SIZE << 10:
        return

    note.content = sanitize_html(note.content)

    note_to_update = db.query(models.Note).get(note_pk)
    old_subject = note_to_update.subject
    old_content = note_to_update.content
    note_to_update.subject = note.subject
    note_to_update.content = note.content
    note_to_update.last_modified_at = datetime.datetime.now()
    note_to_update.last_modified_by_id = user.id

    db_user_created = db.query(models.User).get(note_to_update.created_by_id)

    lb_elem = db.query(models.Labbookchildelement).get(note_to_update.elem_id)
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
            note_to_update.created_by = db_user_created
            note_to_update.last_modified_by = user
            return note_to_update
        db.refresh(note_to_update)
        # ws transmit via event
        note_to_update.created_by = db_user_created
        note_to_update.last_modified_by = user

        # changerecord = [field_name,old_value,new_value]
        # changerecords = [changerecord, changerecord, .....]
        changerecords = [['subject', old_subject, note.subject],
                         ['content', old_content, note.content]]
        # changeset_types:
        # U : edited/updated, R : restored, S: trashed , I initialized/created
        create_note_update_history_entry(db=db,
                                         elem_id=note_pk,
                                         user=user,
                                         object_type_id=30,
                                         changeset_type='U',
                                         changerecords=changerecords)

        update_note_typesense(note_to_update, typesense)
        return note_to_update

    # Second possibility: note is created by admin und user is now not admin
    if check_for_admin_role_with_user_id(db=db,
                                         user_id=note_to_update.created_by_id):
        return None

    if lb_to_update.strict_mode and user.id != note_to_update.created_by_id:
        return None

    if check_for_guest_role(db=db, labbook_pk=lb_elem.labbook_id, user=user):
        return None

    labbook_ids = get_all_labbook_ids_from_non_admin_user(db=db, user=user)

    # Third possibility: consider a note created by non admin
    if lb_elem.labbook_id in labbook_ids:
        try:
            db.commit()
        except SQLAlchemyError as e:
            logger.error(e)
            db.close()
            note_to_update.created_by = db_user_created
            note_to_update.last_modified_by = user
            return note_to_update
        db.refresh(note_to_update)
        # ws transmit via event
        note_to_update.created_by = db_user_created
        note_to_update.last_modified_by = user

        # changerecord = [field_name,old_value,new_value]
        # changerecords = [changerecord, changerecord, .....]
        changerecords = [['subject', None, note.subject],
                         ['content', None, note.content]]
        # changeset_types:
        # U : edited/updated, R : restored, S: trashed , I initialized/created
        create_note_update_history_entry(db=db,
                                         elem_id=note_pk,
                                         user=user,
                                         object_type_id=30,
                                         changeset_type='U',
                                         changerecords=changerecords)

        update_note_typesense(note_to_update, typesense)
        return note_to_update

    return None

def soft_delete_note_typesense(note: Note, typesense: Client):
    try:
        typesense.collections["notes"].documents[str(note.id)].update({"soft_delete": True})
    except TypesenseClientError as e:
        logger.error(e)

# needs to be heavily factorized
def soft_delete_note(db: Session, note_pk, labbook_data, user, typesense: Client):
    note_to_update = db.query(models.Note).get(note_pk)
    note_to_update.deleted = True
    note_to_update.last_modified_at = datetime.datetime.now()
    note_to_update.last_modified_by_id = user.id

    db_user_created = db.query(models.User).get(note_to_update.created_by_id)

    lb_elem = db.query(models.Labbookchildelement).get(note_to_update.elem_id)
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

            note_to_update.created_by = db_user_created
            note_to_update.last_modified_by = user
            return note_to_update
        db.refresh(note_to_update)
        query = db.query(models.Labbookchildelement).filter_by(
            labbook_id=labbook_data.labbook_pk, deleted=False).all()

        if not query:
            try:
                transmit(
                    {'model_name': 'labbook',
                     'model_pk': labbook_data.labbook_pk})
            except RuntimeError as e:
                logger.error(e)

        note_to_update.created_by = db_user_created
        note_to_update.last_modified_by = user

        create_history_entry(db=db,
                             elem_id=note_pk,
                             user=user,
                             object_type_id=30,
                             changeset_type='S',
                             changerecords=[])
        soft_delete_note_typesense(note_to_update, typesense)
        return note_to_update

    if lb_to_update.strict_mode and user.id != note_to_update.created_by_id:
        return None

    # Second possibility: it's a note created by admin
    if check_for_admin_role_with_user_id(db=db,
                                         user_id=note_to_update.created_by_id):

        # allowed only for groupadmins
        if check_for_labbook_admin_access(db=db, labbook_pk=lb_elem.labbook_id,
                                          user=user):
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
                        {'model_name': 'labbook',
                         'model_pk': labbook_data.labbook_pk})
                except RuntimeError as e:
                    logger.error(e)

            note_to_update.created_by = db_user_created
            note_to_update.last_modified_by = user

            create_history_entry(db=db,
                                 elem_id=note_pk,
                                 user=user,
                                 object_type_id=30,
                                 changeset_type='S',
                                 changerecords=[])

            soft_delete_note_typesense(note_to_update, typesense)
            return note_to_update
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
            return note_to_update
        db.refresh(note_to_update)
        query = db.query(models.Labbookchildelement).filter_by(
            labbook_id=labbook_data.labbook_pk, deleted=False).all()

        if not query:
            try:
                transmit(
                    {'model_name': 'labbook',
                     'model_pk': labbook_data.labbook_pk})
            except RuntimeError as e:
                logger.error(e)

        note_to_update.created_by = db_user_created
        note_to_update.last_modified_by = user

        create_history_entry(db=db,
                             elem_id=note_pk,
                             user=user,
                             object_type_id=30,
                             changeset_type='S',
                             changerecords=[])
        soft_delete_note_typesense(note_to_update, typesense)
        return note_to_update

    return None

def restore_note_typesense(note: Note, typesense: Client):
    try:
        typesense.collections["notes"].documents[str(note.id)].update({"soft_delete": False})
    except TypesenseClientError as e:
        logger.error(e)

def restore_note(db: Session, note_pk, user, typesense: Client):
    note_to_update = db.query(models.Note).get(note_pk)
    note_to_update.deleted = False
    note_to_update.last_modified_at = datetime.datetime.now()
    note_to_update.last_modified_by_id = user.id

    db_user_created = db.query(models.User).get(note_to_update.created_by_id)

    lb_elem = db.query(models.Labbookchildelement).get(note_to_update.elem_id)
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
            return note_to_update
        db.refresh(note_to_update)

        note_to_update.created_by = db_user_created
        note_to_update.last_modified_by = user

        create_history_entry(db=db,
                             elem_id=note_pk,
                             user=user,
                             object_type_id=30,
                             changeset_type='R',
                             changerecords=[])
        restore_note_typesense(note_to_update, typesense)
        return note_to_update

    # Second possibility: it's a note created by admin
    if check_for_admin_role_with_user_id(db=db,
                                         user_id=note_to_update.created_by_id):
        logger.info('created by')

        # allowed only for groupadmins
        if check_for_labbook_admin_access(db=db, labbook_pk=lb_elem.labbook_id,
                                          user=user):
            try:
                db.commit()
            except SQLAlchemyError as e:
                logger.error(e)
                db.close()
                return note_to_update
            db.refresh(note_to_update)
            note_to_update.created_by = db_user_created
            note_to_update.last_modified_by = user

            create_history_entry(db=db,
                                 elem_id=note_pk,
                                 user=user,
                                 object_type_id=30,
                                 changeset_type='R',
                                 changerecords=[])
            restore_note_typesense(note_to_update, typesense)
            return note_to_update
        else:
            return None

    if check_for_guest_role(db=db, labbook_pk=lb_elem.labbook_id, user=user):
        return None

    labbook_ids = get_all_labbook_ids_from_non_admin_user(db=db, user=user)

    if lb_elem.labbook_id in labbook_ids:
        logger.info('in labbook ids')
        try:
            db.commit()
        except SQLAlchemyError as e:
            logger.error(e)
            db.close()
            return note_to_update
        db.refresh(note_to_update)

        note_to_update.created_by = db_user_created
        note_to_update.last_modified_by = user

        create_history_entry(db=db,
                             elem_id=note_pk,
                             user=user,
                             object_type_id=30,
                             changeset_type='R',
                             changerecords=[])
        restore_note_typesense(note_to_update, typesense)
        return note_to_update

    return None


def get_note_export_link(db: Session, note_pk, user):
    db_note = db.query(models.Note).get(note_pk)
    db_note = build_note_download_url_with_token(note_to_process=db_note,
                                                 user=user)
    lb_elem = db.query(models.Labbookchildelement).get(db_note.elem_id)
    export_link = {
        'url': db_note.path,
        'filename': f'{db_note.subject}.pdf'
    }

    if user.admin or check_for_labbook_access(
            db=db, labbook_pk=lb_elem.labbook_id,
            user=user):
        return export_link

    return None


def build_note_download_url_with_token(note_to_process, user):
    access_token_expires = security.timedelta(
        minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    note_to_process.path = f'{URL_BASE_PATH}notes/{note_to_process.id}/export?jwt={security.Token(access_token=access_token, token_type="bearer").access_token}'
    return note_to_process


def get_all_deleted_notes(db: Session):
    notes = db.query(models.Note).filter_by(
        deleted=True).order_by(text('subject asc')).all()
    return notes


def remove_soft_deleted_note(db: Session, note_pk):
    note_to_remove = db.query(models.Note).get(note_pk)
    if note_to_remove and note_to_remove.deleted:
        lb_elem = db.query(models.Labbookchildelement).get(
            note_to_remove.elem_id)
        relations = db.query(models.Relation).filter_by(
            right_object_id=note_pk, left_content_type=70).all()
        db.delete(note_to_remove)
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
        return True
    return
