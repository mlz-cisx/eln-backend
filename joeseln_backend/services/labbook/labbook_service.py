import pathlib

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import text

from sqlalchemy import or_

from typesense.client import Client
from typesense.exceptions import TypesenseClientError

from joeseln_backend.full_text_search.html_stripper import strip_html_and_binary
from joeseln_backend.models import models
from joeseln_backend.services.history.history_service import \
    create_history_entry
from joeseln_backend.services.labbook.labbook_schemas import *
from joeseln_backend.services.user_to_group.user_to_group_service import \
    get_user_group_roles, get_user_group_roles_with_match, \
    get_user_groups, get_user_groups_role_groupadmin
from joeseln_backend.services.privileges.admin_privileges.privileges_service import \
    ADMIN
from joeseln_backend.services.privileges.privileges_service import \
    create_labbook_privileges
from joeseln_backend.auth import security
from joeseln_backend.helper import db_ordering
from joeseln_backend.conf.base_conf import URL_BASE_PATH, PICTURES_BASE_PATH, \
    FILES_BASE_PATH

from joeseln_backend.mylogging.root_logger import logger
from joeseln_backend.conf.base_conf import LABBOOK_QUERY_MODE
from joeseln_backend.ws.ws_client import transmit


def check_for_labbook_access(db: Session, labbook_pk, user):
    if not user.admin:
        user_groups = get_user_groups(db=db, username=user.username)

        if len(user_groups) == 0:
            return False
        if LABBOOK_QUERY_MODE == 'match':
            db_lb = db.query(models.Labbook).filter(
                or_(*[models.Labbook.title.contains(name) for name in
                      user_groups])).filter(
                models.Labbook.id == labbook_pk).first()
        else:
            db_lb = db.query(models.Labbook).filter(
                models.Labbook.title.in_(user_groups),
                models.Labbook.id == labbook_pk).first()

        if not db_lb:
            return False
    return True


def create_note_below(db: Session, element_pk, user,
                      typesense_client: Client):
    db_labbook_elem = db.query(models.Labbookchildelement).get(element_pk)
    if not db_labbook_elem or \
            not check_for_labbook_access(db=db,
                                         labbook_pk=db_labbook_elem.labbook_id,
                                         user=user):
        return False

    labbook_id = db_labbook_elem.labbook_id
    query = db.query(models.Labbookchildelement).filter_by(
        labbook_id=labbook_id, deleted=False).order_by(
        models.Labbookchildelement.position_y).all()

    elem_nw_x = db_labbook_elem.position_x
    elem_ne_x = db_labbook_elem.position_x + db_labbook_elem.width
    elem_y = db_labbook_elem.position_y + db_labbook_elem.height
    elem_top_y = db_labbook_elem.position_y

    new_x = db_labbook_elem.position_x
    new_y = elem_y
    new_width = db_labbook_elem.width
    new_height = 5

    has_to_be_shifted = False
    rows = 5
    conflict_elem_position_y = 0

    for elem in query:
        if elem.id != db_labbook_elem.id and elem.position_y >= elem_top_y and elem_ne_x > elem.position_x >= elem_nw_x \
                and elem.position_y < elem_y + rows:
            has_to_be_shifted = True
            conflict_elem_position_y = elem.position_y
            break
        if elem.id != db_labbook_elem.id and elem.position_y >= elem_top_y \
                and elem_ne_x >= elem.position_x + elem.width > elem_nw_x \
                and elem.position_y < elem_y + rows:
            has_to_be_shifted = True
            conflict_elem_position_y = elem.position_y
            break

        if elem.id != db_labbook_elem.id and elem.position_y >= elem_top_y \
                and elem_ne_x < elem.position_x + elem.width and elem.position_x < elem_nw_x \
                and elem.position_y < elem_y + rows:
            has_to_be_shifted = True
            conflict_elem_position_y = elem.position_y
            break

    if has_to_be_shifted:
        shift = elem_y + rows - conflict_elem_position_y
        for elem in query:
            if elem.position_y >= conflict_elem_position_y:
                elem.position_y = elem.position_y + shift

        try:
            db.commit()
        except SQLAlchemyError as e:
            logger.error(e)
            db.close()

            return False

    db_note = models.Note(version_number=0,
                          subject='Text',
                          content='',
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
        return False

    db.refresh(db_note)
    # changerecord = [field_name,old_value,new_value]
    # changerecords = [changerecord, changerecord, .....]
    changerecords = [['subject', None, 'Text'],
                     ['content', None, '']]
    # changeset_types:
    # U : edited/updated, R : restored, S: trashed , I initialized/created

    create_history_entry(db=db,
                         elem_id=db_note.id,
                         user=user,
                         object_type_id=30,
                         changeset_type='I',
                         changerecords=changerecords)

    try:
        document = {
            'subject': 'Text',
            'content': '',
            'last_modified_at': int(datetime.datetime.now().timestamp())}
        typesense_client.collections['notes'].documents[str(db_note.id)].update(
            document)
    except TypesenseClientError as e:
        logger.error(e)

    db_labbook_elem = models.Labbookchildelement(
        labbook_id=labbook_id,
        position_x=new_x,
        position_y=new_y,
        width=new_width,
        height=new_height,
        child_object_id=db_note.id,
        child_object_content_type=30,
        child_object_content_type_model='shared_elements.note',
        version_number=0,
        created_at=datetime.datetime.now(),
        created_by_id=user.id,
        last_modified_at=datetime.datetime.now(),
        last_modified_by_id=user.id
    )

    db.add(db_labbook_elem)
    lb_to_update = db.query(models.Labbook).get(labbook_id)
    lb_to_update.last_modified_at = datetime.datetime.now()
    lb_to_update.last_modified_by_id = user.id

    try:
        db.commit()
    except SQLAlchemyError as e:
        logger.error(e)
        db.close()
        return False

    db.refresh(db_labbook_elem)

    note = db.query(models.Note).get(db_note.id)
    note.elem_id = db_labbook_elem.id
    try:
        db.commit()
    except SQLAlchemyError as e:
        logger.error(e)
        db.close()
        return False

    try:
        # insert note to typesense for searching purpose
        stripped_content = strip_html_and_binary(note.content)
        typesense_client.collections['notes'].documents.upsert(
            {'id': str(note.id),
             'elem_id': str(
                 db_labbook_elem.id),
             'subject': note.subject,
             'content': stripped_content,
             'last_modified_at': int(
                 note.last_modified_at.timestamp()),
             'labbook_id': str(
                 labbook_id),
             'soft_delete': False})
    except TypesenseClientError as e:
        logger.error(e)

    try:
        transmit({'model_name': 'labbook', 'model_pk': str(labbook_id)})
    except RuntimeError as e:
        logger.error(e)

    return True


def create_note_aside(db: Session, element_pk, user,
                      typesense_client: Client):
    db_labbook_elem = db.query(models.Labbookchildelement).get(element_pk)
    if not db_labbook_elem or \
            not check_for_labbook_access(db=db,
                                         labbook_pk=db_labbook_elem.labbook_id,
                                         user=user):
        return False

    labbook_id = db_labbook_elem.labbook_id
    query = db.query(models.Labbookchildelement).filter_by(
        labbook_id=labbook_id, deleted=False).order_by(
        models.Labbookchildelement.position_y).all()

    elem_ne_x = db_labbook_elem.position_x + db_labbook_elem.width
    elem_ne_y = db_labbook_elem.position_y
    elem_se_y = db_labbook_elem.position_y + db_labbook_elem.height

    # minItemCols : 5
    if elem_ne_x > 15:
        return False

    new_x = elem_ne_x
    new_y = elem_ne_y
    new_width = 20 - new_x
    new_height = db_labbook_elem.height

    insertion_possible = True
    for elem in query:
        # elem overlaps from top
        if elem.position_x >= elem_ne_x and elem_se_y >= (
                elem.position_y + elem.height) > elem_ne_y:
            insertion_possible = False
            break
        # elem overlaps from bottom
        if elem.position_x >= elem_ne_x and elem_se_y >= (
                elem.position_y + 1) > elem_ne_y:
            insertion_possible = False
            break
        # db_labbook_elem overlaps elem
        if elem.position_x >= elem_ne_x and elem_se_y < (
                elem.position_y + elem.height) and elem.position_y + 1 <= elem_ne_y:
            insertion_possible = False
            break

    if not insertion_possible:
        return False

    db_note = models.Note(version_number=0,
                          subject='Text',
                          content='',
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
        return False

    db.refresh(db_note)
    # changerecord = [field_name,old_value,new_value]
    # changerecords = [changerecord, changerecord, .....]
    changerecords = [['subject', None, 'Text'],
                     ['content', None, '']]
    # changeset_types:
    # U : edited/updated, R : restored, S: trashed , I initialized/created

    create_history_entry(db=db,
                         elem_id=db_note.id,
                         user=user,
                         object_type_id=30,
                         changeset_type='I',
                         changerecords=changerecords)

    try:
        document = {
            'subject': 'Text',
            'content': '',
            'last_modified_at': int(datetime.datetime.now().timestamp())}
        typesense_client.collections['notes'].documents[str(db_note.id)].update(
            document)
    except TypesenseClientError as e:
        logger.error(e)

    db_labbook_elem = models.Labbookchildelement(
        labbook_id=labbook_id,
        position_x=new_x,
        position_y=new_y,
        width=new_width,
        height=new_height,
        child_object_id=db_note.id,
        child_object_content_type=30,
        child_object_content_type_model='shared_elements.note',
        version_number=0,
        created_at=datetime.datetime.now(),
        created_by_id=user.id,
        last_modified_at=datetime.datetime.now(),
        last_modified_by_id=user.id
    )

    db.add(db_labbook_elem)
    lb_to_update = db.query(models.Labbook).get(labbook_id)
    lb_to_update.last_modified_at = datetime.datetime.now()
    lb_to_update.last_modified_by_id = user.id

    try:
        db.commit()
    except SQLAlchemyError as e:
        logger.error(e)
        db.close()
        return False

    db.refresh(db_labbook_elem)

    note = db.query(models.Note).get(db_note.id)
    note.elem_id = db_labbook_elem.id
    try:
        db.commit()
    except SQLAlchemyError as e:
        logger.error(e)
        db.close()
        return False

    try:
        # insert note to typesense for searching purpose
        stripped_content = strip_html_and_binary(note.content)
        typesense_client.collections['notes'].documents.upsert(
            {'id': str(note.id),
             'elem_id': str(
                 db_labbook_elem.id),
             'subject': note.subject,
             'content': stripped_content,
             'last_modified_at': int(
                 note.last_modified_at.timestamp()),
             'labbook_id': str(
                 labbook_id),
             'soft_delete': False})
    except TypesenseClientError as e:
        logger.error(e)

    try:
        transmit({'model_name': 'labbook', 'model_pk': str(labbook_id)})
    except RuntimeError as e:
        logger.error(e)

    return True


def check_for_labbook_admin_access(db: Session, labbook_pk, user):
    if not user.admin:
        user_groups = get_user_groups_role_groupadmin(db=db,
                                                      username=user.username)
        if len(user_groups) == 0:
            return False

        if LABBOOK_QUERY_MODE == 'match':
            db_lb = db.query(models.Labbook).filter(
                or_(*[models.Labbook.title.contains(name) for name in
                      user_groups])).filter(
                models.Labbook.id == labbook_pk).first()
        else:
            db_lb = db.query(models.Labbook).filter(
                models.Labbook.title.in_(user_groups),
                models.Labbook.id == labbook_pk).first()

        if not db_lb:
            return False
    return True


def get_all_labbook_ids_from_non_admin_user(db: Session, user):
    labbooks = []
    if LABBOOK_QUERY_MODE == 'match':
        labbooks = db.query(models.Labbook).join(models.Group,
                                                 models.Labbook.title.contains(
                                                     models.Group.groupname)).join(
            models.UserToGroupRole,
            models.Group.id == models.UserToGroupRole.group_id).join(
            models.User,
            models.UserToGroupRole.user_id == models.User.id).filter(
            models.User.username == user.username).all()
    elif LABBOOK_QUERY_MODE == 'equal':
        labbooks = db.query(models.Labbook).join(models.Group,
                                                 models.Group.groupname == models.Labbook.title).join(
            models.UserToGroupRole,
            models.Group.id == models.UserToGroupRole.group_id).join(
            models.User,
            models.UserToGroupRole.user_id == models.User.id).filter(
            models.User.username == user.username).all()

    return [x.id for x in labbooks]


def get_labbooks_from_user(db: Session, params, user):
    order_params = db_ordering.get_order_params(ordering=params.get('ordering'))
    if user.admin:
        if params.get('search'):
            search_text = params.get('search')
            lbs = db.query(models.Labbook).filter(
                models.Labbook.title.ilike(f'%{search_text}%')).filter_by(
                deleted=bool(params.get('deleted'))).order_by(
                text(order_params)).offset(params.get('offset')).limit(
                params.get('limit')).all()
        else:
            lbs = db.query(models.Labbook).filter_by(
                deleted=bool(params.get('deleted'))).order_by(
                text(order_params)).offset(params.get('offset')).limit(
                params.get('limit')).all()
        for lb in lbs:
            db_user_created = db.query(models.User).get(lb.created_by_id)
            db_user_modified = db.query(models.User).get(
                lb.last_modified_by_id)
            lb.created_by = db_user_created
            lb.last_modified_by = db_user_modified
            lb.length = db.query(models.Labbookchildelement).filter_by(
                labbook_id=lb.id, deleted=False).count()
        return lbs

    if order_params:
        order_text = f'labbook.{order_params}'
    else:
        order_text = ''

    labbooks = []
    if LABBOOK_QUERY_MODE == 'match':
        if params.get('search'):
            search_text = params.get('search')
            labbooks = db.query(models.Labbook).join(models.Group,
                                                     models.Labbook.title.contains(
                                                         models.Group.groupname)).join(
                models.UserToGroupRole,
                models.Group.id == models.UserToGroupRole.group_id).join(
                models.User,
                models.UserToGroupRole.user_id == models.User.id).filter(
                models.Labbook.title.ilike(f'%{search_text}%')).filter(
                models.Labbook.deleted == bool(params.get('deleted'))).filter(
                models.User.username == user.username).order_by(
                text(order_text)).offset(params.get('offset')).limit(
                params.get('limit')).all()
        else:
            labbooks = db.query(models.Labbook).join(models.Group,
                                                     models.Labbook.title.contains(
                                                         models.Group.groupname)).join(
                models.UserToGroupRole,
                models.Group.id == models.UserToGroupRole.group_id).join(
                models.User,
                models.UserToGroupRole.user_id == models.User.id).filter(
                models.Labbook.deleted == bool(params.get('deleted'))).filter(
                models.User.username == user.username).order_by(
                text(order_text)).offset(params.get('offset')).limit(
                params.get('limit')).all()
    elif LABBOOK_QUERY_MODE == 'equal':
        if params.get('search'):
            search_text = params.get('search')
            labbooks = db.query(models.Labbook).join(models.Group,
                                                     models.Group.groupname == models.Labbook.title).join(
                models.UserToGroupRole,
                models.Group.id == models.UserToGroupRole.group_id).join(
                models.User,
                models.UserToGroupRole.user_id == models.User.id).filter(
                models.Labbook.title.ilike(f'%{search_text}%')).filter(
                models.Labbook.deleted == bool(params.get('deleted'))).filter(
                models.User.username == user.username).order_by(
                text(order_text)).offset(params.get('offset')).limit(
                params.get('limit')).all()
        else:
            labbooks = db.query(models.Labbook).join(models.Group,
                                                     models.Group.groupname == models.Labbook.title).join(
                models.UserToGroupRole,
                models.Group.id == models.UserToGroupRole.group_id).join(
                models.User,
                models.UserToGroupRole.user_id == models.User.id).filter(
                models.Labbook.deleted == bool(params.get('deleted'))).filter(
                models.User.username == user.username).order_by(
                text(order_text)).offset(params.get('offset')).limit(
                params.get('limit')).all()

    for lb in labbooks:
        db_user_created = db.query(models.User).get(lb.created_by_id)
        db_user_modified = db.query(models.User).get(
            lb.last_modified_by_id)
        lb.created_by = db_user_created
        lb.last_modified_by = db_user_modified
        lb.length = db.query(models.Labbookchildelement).filter_by(
            labbook_id=lb.id, deleted=False).count()

    return labbooks


def create_labbook(db: Session, labbook: LabbookCreate, user):
    db_labbook = None
    if user.admin:
        db_labbook = models.Labbook(version_number=0,
                                    title=labbook.title,
                                    description=labbook.description,
                                    created_at=datetime.datetime.now(),
                                    created_by_id=user.id,
                                    last_modified_at=datetime.datetime.now(),
                                    last_modified_by_id=user.id)
        db.add(db_labbook)
        try:
            db.commit()
        except SQLAlchemyError as e:
            logger.error(e)
            db.close()
            return None
        db.refresh(db_labbook)
        db_user_created = db.query(models.User).get(db_labbook.created_by_id)
        db_user_modified = db.query(models.User).get(
            db_labbook.last_modified_by_id)
        db_labbook.created_by = db_user_created
        db_labbook.last_modified_by = db_user_modified

        # changerecord = [field_name,old_value,new_value]
        # changerecords = [changerecord, changerecord, .....]
        changerecords = [['title', None, labbook.title],
                         ['description', None, labbook.description]]
        # changeset_types:
        # U : edited/updated, R : restored, S: trashed , I initialized/created
        create_history_entry(db=db,
                             elem_id=db_labbook.id,
                             user=user,
                             object_type_id=10,
                             changeset_type='I',
                             changerecords=changerecords)

    return db_labbook


def get_labbook_for_export(db: Session, labbook_pk):
    db_labbook = db.query(models.Labbook).get(labbook_pk)
    db_user = db.query(models.User).get(db_labbook.created_by_id)
    db_labbook.created_by = db_user
    return db_labbook


def get_labbook_with_privileges(db: Session, labbook_pk, user):
    if user.admin:
        lb = db.query(models.Labbook).get(labbook_pk)
        if lb:
            db_user_created = db.query(models.User).get(lb.created_by_id)
            db_user_modified = db.query(models.User).get(
                lb.last_modified_by_id)
            lb.created_by = db_user_created
            lb.last_modified_by = db_user_modified

            return {'privileges': ADMIN,
                    'labbook': lb}
        return None

    user_groups = get_user_groups(db=db, username=user.username)
    if len(user_groups) == 0:
        return None
    db_lb = None
    if LABBOOK_QUERY_MODE == 'match':
        db_lb = db.query(models.Labbook).filter(
            or_(*[models.Labbook.title.contains(name) for name in
                  user_groups])).filter(models.Labbook.id == labbook_pk).first()
    elif LABBOOK_QUERY_MODE == 'equal':
        db_lb = db.query(models.Labbook).filter(
            models.Labbook.title.in_(user_groups),
            models.Labbook.id == labbook_pk).first()

    if db_lb:
        if LABBOOK_QUERY_MODE == 'match':
            user_roles = get_user_group_roles_with_match(db=db,
                                                         username=user.username,
                                                         groupname=db_lb.title)

            privileges = create_labbook_privileges(user_roles=user_roles)
        else:
            user_roles = get_user_group_roles(db=db,
                                              username=user.username,
                                              groupname=db_lb.title)

            privileges = create_labbook_privileges(user_roles=user_roles)

        db_user_created = db.query(models.User).get(db_lb.created_by_id)
        db_user_modified = db.query(models.User).get(
            db_lb.last_modified_by_id)
        db_lb.created_by = db_user_created
        db_lb.last_modified_by = db_user_modified

        return {'privileges': privileges, 'labbook': db_lb}

    return None


def patch_labbook(db: Session, labbook_pk, labbook: LabbookPatch, user):
    db_labbook = db.query(models.Labbook).get(labbook_pk)
    lb_privileges = None
    if user.admin:
        lb_privileges = ADMIN
    elif LABBOOK_QUERY_MODE == 'match':
        user_roles = get_user_group_roles_with_match(db=db,
                                                     username=user.username,
                                                     groupname=db_labbook.title)
        lb_privileges = create_labbook_privileges(user_roles=user_roles)

    elif LABBOOK_QUERY_MODE == 'equal':
        user_roles = get_user_group_roles(db=db,
                                          username=user.username,
                                          groupname=db_labbook.title)

        lb_privileges = create_labbook_privileges(user_roles=user_roles)
    changerecords = []
    if lb_privileges['edit']:
        # it is patched with form-input labbook page
        if labbook.title:
            old_labbook_title = db_labbook.title
            old_labbook_strict_mode = db_labbook.strict_mode
            db_labbook.title = labbook.title
            db_labbook.strict_mode = labbook.strict_mode

            changerecords = [['title', old_labbook_title, labbook.title],
                             ['strict mode', old_labbook_strict_mode,
                              labbook.strict_mode]]

        # it is patched with description modal
        elif not labbook.title:
            old_labbook_description = db_labbook.description
            db_labbook.description = f'{labbook.description} '
            changerecords = [['description', old_labbook_description,
                              f'{labbook.description} ']]
        db_labbook.last_modified_at = datetime.datetime.now()
        db_labbook.last_modified_by_id = user.id
        try:
            db.commit()
        except SQLAlchemyError as e:
            logger.error(e)
            db.close()
            return db_labbook
        db.refresh(db_labbook)

        create_history_entry(db=db,
                             elem_id=labbook_pk,
                             user=user,
                             object_type_id=10,
                             changeset_type='U',
                             changerecords=changerecords)

    # TODO use ws?
    # try:
    #     transmit({'model_name': 'labbook', 'model_pk': str(labbook_pk)})
    # except RuntimeError as e:
    #     print(e)
    db_user_created = db.query(models.User).get(db_labbook.created_by_id)
    db_user_modified = db.query(models.User).get(
        db_labbook.last_modified_by_id)
    db_labbook.created_by = db_user_created
    db_labbook.last_modified_by = db_user_modified

    return db_labbook


def get_labbook_export_link(db: Session, labbook_pk, user):
    if not user.admin:
        user_groups = get_user_groups(db=db, username=user.username)
        if len(user_groups) == 0:
            return None
        db_lb = db.query(models.Labbook).filter(
            or_(*[models.Labbook.title.contains(name) for name in
                  user_groups])).filter(
            models.Labbook.id == labbook_pk).first()
        if not db_lb:
            return None
    else:
        db_lb = db.query(models.Labbook).get(labbook_pk)

    db_labbook = build_labbook_download_url_with_token(lb_to_process=db_lb,
                                                       user=user)
    export_link = {
        'url': db_labbook.path,
        'filename': db_labbook.title
    }

    return export_link


def build_labbook_download_url_with_token(lb_to_process, user):
    access_token_expires = security.timedelta(
        minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    lb_to_process.path = f'{URL_BASE_PATH}labbooks/{lb_to_process.id}/export?jwt={security.Token(access_token=access_token, token_type="bearer").access_token}'
    return lb_to_process


def soft_delete_labbook(db: Session, labbook_uuid, username):
    user = db.query(models.User).filter_by(username=username).first()
    db_labbook = db.query(models.Labbook).filter_by(id=labbook_uuid,
                                                    deleted=False).first()
    if db_labbook:
        db_labbook.deleted = True
        db_labbook.last_modified_at = datetime.datetime.now()
        db_labbook.last_modified_by_id = user.id
        try:
            db.commit()
        except SQLAlchemyError as e:
            logger.error(e)
            db.close()
            return
        db.refresh(db_labbook)
        return True
    return


def gui_soft_delete_labbook(db: Session, labbook_uuid, user):
    if user.admin:
        db_labbook = db.query(models.Labbook).get(labbook_uuid)
        if db_labbook and not db_labbook.deleted:
            db_labbook.deleted = True
            db_labbook.last_modified_at = datetime.datetime.now()
            db_labbook.last_modified_by_id = user.id
            try:
                db.commit()
            except SQLAlchemyError as e:
                logger.error(e)
                db.close()
                return
            db.refresh(db_labbook)
            db_user_created = db.query(models.User).get(
                db_labbook.created_by_id)
            db_user_modified = db.query(models.User).get(
                db_labbook.last_modified_by_id)
            db_labbook.created_by = db_user_created
            db_labbook.last_modified_by = db_user_modified
            return db_labbook
        return
    return


def restore_labbook(db: Session, labbook_uuid, username):
    user = db.query(models.User).filter_by(username=username).first()
    db_labbook = db.query(models.Labbook).filter_by(id=labbook_uuid,
                                                    deleted=True).first()
    if db_labbook:
        db_labbook.deleted = False
        db_labbook.last_modified_at = datetime.datetime.now()
        db_labbook.last_modified_by_id = user.id
        try:
            db.commit()
        except SQLAlchemyError as e:
            logger.error(e)
            db.close()
            return
        db.refresh(db_labbook)
        return True
    return


def gui_restore_labbook(db: Session, labbook_uuid, user):
    if user.admin:
        db_labbook = db.query(models.Labbook).get(labbook_uuid)
        if db_labbook and db_labbook.deleted:
            db_labbook.deleted = False
            db_labbook.last_modified_at = datetime.datetime.now()
            db_labbook.last_modified_by_id = user.id
            try:
                db.commit()
            except SQLAlchemyError as e:
                logger.error(e)
                db.close()
                return
            db.refresh(db_labbook)
            db_user_created = db.query(models.User).get(
                db_labbook.created_by_id)
            db_user_modified = db.query(models.User).get(
                db_labbook.last_modified_by_id)
            db_labbook.created_by = db_user_created
            db_labbook.last_modified_by = db_user_modified
            return db_labbook
        return
    return


def get_deleted_labbooks(db: Session):
    return db.query(models.Labbook).filter_by(
        deleted=True).order_by(text('title asc')).all()


def get_non_deleted_labbooks(db: Session):
    return db.query(models.Labbook).filter_by(
        deleted=False).order_by(text('title asc')).all()


def remove_deleted_labbook_with_its_content(db: Session, labbook_uuid):
    db_labbook = db.query(models.Labbook).filter_by(id=labbook_uuid,
                                                    deleted=True).first()
    if db_labbook:
        elems = db.query(models.Labbookchildelement).filter_by(
            labbook_id=labbook_uuid).all()
        for elem in elems:
            # note
            if elem.child_object_content_type == 30:
                note_to_remove = db.query(models.Note).get(elem.child_object_id)
                relations = db.query(models.Relation).filter_by(
                    right_object_id=elem.child_object_id,
                    left_content_type=70).all()
                db.delete(note_to_remove)
                # it has to be committed first because of foreign key dependency
                try:
                    db.commit()
                except SQLAlchemyError as e:
                    print(e)
                db.delete(elem)
                for relation in relations:
                    db.delete(relation)
                try:
                    db.commit()
                except SQLAlchemyError as e:
                    print(e)
                print(f'{note_to_remove.subject} removed')

            if elem.child_object_content_type == 40:
                pic_to_remove = db.query(models.Picture).get(
                    elem.child_object_id)

                ri_img_path = f'{PICTURES_BASE_PATH}{pic_to_remove.rendered_image}'
                bi_img_path = f'{PICTURES_BASE_PATH}{pic_to_remove.background_image}'
                shapes_path = f'{PICTURES_BASE_PATH}{pic_to_remove.shapes_image}'

                relations = db.query(models.Relation).filter_by(
                    right_object_id=elem.child_object_id,
                    left_content_type=70).all()
                db.delete(pic_to_remove)
                # it has to be committed first because of foreign key dependency
                try:
                    db.commit()
                except SQLAlchemyError as e:
                    print(e)
                db.delete(elem)
                for relation in relations:
                    db.delete(relation)
                try:
                    db.commit()
                except SQLAlchemyError as e:
                    print(e)

                try:
                    file_to_rem = pathlib.Path(ri_img_path)
                    file_to_rem.unlink()
                except FileNotFoundError as e:
                    print(e)
                try:
                    file_to_rem = pathlib.Path(bi_img_path)
                    file_to_rem.unlink()
                except FileNotFoundError as e:
                    print(e)
                try:
                    file_to_rem = pathlib.Path(shapes_path)
                    file_to_rem.unlink()
                except FileNotFoundError as e:
                    print(e)

                print(f'{pic_to_remove.title} removed')

            if elem.child_object_content_type == 50:
                file_to_remove = db.query(models.File).get(elem.child_object_id)
                file_path = f'{FILES_BASE_PATH}{file_to_remove.path}'
                # only comment relations
                relations = db.query(models.Relation).filter_by(
                    right_object_id=elem.child_object_id,
                    left_content_type=70).all()
                db.delete(file_to_remove)
                # it has to be committed first because of foreign key dependency
                try:
                    db.commit()
                except SQLAlchemyError as e:
                    print(e)
                try:
                    file_to_rem = pathlib.Path(file_path)
                    file_to_rem.unlink()
                except FileNotFoundError as e:
                    print(e)

                db.delete(elem)
                for relation in relations:
                    db.delete(relation)
                try:
                    db.commit()
                except SQLAlchemyError as e:
                    print(e)

        db.delete(db_labbook)
        try:
            db.commit()
        except SQLAlchemyError as e:
            print(e)
            return

        return True

    return
