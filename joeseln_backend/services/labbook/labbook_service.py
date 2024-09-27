from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import text

from sqlalchemy import or_

from joeseln_backend.models import models
from joeseln_backend.services.labbook.labbook_schemas import *
from joeseln_backend.services.user_to_group.user_to_group_service import \
    get_user_group_roles, get_user_group_roles_with_match, check_for_admin_role, \
    get_user_groups
from joeseln_backend.services.privileges.admin_privileges.privileges_service import \
    ADMIN
from joeseln_backend.services.privileges.privileges_service import \
    create_labbook_privileges
from joeseln_backend.auth import security
from joeseln_backend.helper import db_ordering
from joeseln_backend.conf.base_conf import URL_BASE_PATH
from joeseln_backend.conf.mocks.mock_user import FAKE_USER_ID

from joeseln_backend.mylogging.root_logger import logger
from joeseln_backend.conf.base_conf import LABBOOK_QUERY_MODE


def get_labbooks(db: Session, params):
    order_params = db_ordering.get_order_params(ordering=params.get('ordering'))
    return db.query(models.Labbook).filter_by(
        deleted=bool(params.get('deleted'))).order_by(
        text(order_params)).offset(params.get('offset')).limit(
        params.get('limit')).all()


def check_for_labbook_access(db: Session, labbook_pk, user):
    if not check_for_admin_role(db=db, username=user.username):
        user_groups = get_user_groups(db=db, username=user.username)
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


def get_labbooks_from_user(db: Session, params, user):
    order_params = db_ordering.get_order_params(ordering=params.get('ordering'))
    if check_for_admin_role(db=db, username=user.username):
        return db.query(models.Labbook).filter_by(
            deleted=bool(params.get('deleted'))).order_by(
            text(order_params)).offset(params.get('offset')).limit(
            params.get('limit')).all()
    if order_params:
        order_text = f'labbook.{order_params}'
    else:
        order_text = ''

    labbooks = []
    if LABBOOK_QUERY_MODE == 'match':
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

    return labbooks


def create_labbook(db: Session, labbook: LabbookCreate, user):
    db_labbook = None
    if check_for_admin_role(db=db, username=user.username):
        db_labbook = models.Labbook(version_number=0,
                                    title=labbook.title,
                                    description=labbook.description,
                                    created_at=datetime.datetime.now(),
                                    created_by_id=FAKE_USER_ID,
                                    last_modified_at=datetime.datetime.now(),
                                    last_modified_by_id=FAKE_USER_ID)
        db.add(db_labbook)
        try:
            db.commit()
        except SQLAlchemyError as e:
            logger.error(e)
        db.refresh(db_labbook)
    return db_labbook


def get_labbook_for_export(db: Session, labbook_pk):
    return db.query(models.Labbook).get(labbook_pk)


def get_labbook_with_privileges(db: Session, labbook_pk, user):
    if check_for_admin_role(db=db, username=user.username):
        return {'privileges': ADMIN,
                'labbook': db.query(models.Labbook).get(labbook_pk)}

    user_groups = get_user_groups(db=db, username=user.username)
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

        return {'privileges': privileges, 'labbook': db_lb}

    return None


def patch_labbook(db: Session, labbook_pk, labbook: LabbookPatch, user):
    db_labbook = db.query(models.Labbook).get(labbook_pk)
    lb_privileges = None
    if check_for_admin_role(db=db, username=user.username):
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

    if lb_privileges['edit']:
        db_labbook.title = labbook.title
        db_labbook.last_modified_at = datetime.datetime.now()
        db_labbook.last_modified_by_id = FAKE_USER_ID
        try:
            db.commit()
        except SQLAlchemyError as e:
            logger.error(e)
        db.refresh(db_labbook)
    # TODO use ws?
    # try:
    #     transmit({'model_name': 'labbook', 'model_pk': str(labbook_pk)})
    # except RuntimeError as e:
    #     print(e)

    return db_labbook


def get_labbook_export_link(db: Session, labbook_pk, user):
    if not check_for_admin_role(db=db, username=user.username):
        user_groups = get_user_groups(db=db, username=user.username)
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
