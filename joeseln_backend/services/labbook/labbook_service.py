from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import text

from joeseln_backend.models import models
from joeseln_backend.services.labbook.labbook_schemas import *
from joeseln_backend.services.user_to_group.user_to_group_service import \
    get_user_group_roles
from joeseln_backend.services.privileges.privileges_service import \
    create_labbook_privileges
from joeseln_backend.auth import security
from joeseln_backend.helper import db_ordering
from joeseln_backend.conf.base_conf import URL_BASE_PATH
from joeseln_backend.conf.mocks.mock_user import FAKE_USER_ID

from joeseln_backend.mylogging.root_logger import logger


def get_labbooks(db: Session, params):
    order_params = db_ordering.get_order_params(ordering=params.get('ordering'))
    return db.query(models.Labbook).filter_by(
        deleted=bool(params.get('deleted'))).order_by(
        text(order_params)).offset(params.get('offset')).limit(
        params.get('limit')).all()


def get_labbooks_from_user(db: Session, params, user):
    logger.info(user.username)
    # TODO filter with roles in realm_access from user
    order_params = db_ordering.get_order_params(ordering=params.get('ordering'))
    return db.query(models.Labbook).filter_by(
        deleted=bool(params.get('deleted'))).order_by(
        text(order_params)).offset(params.get('offset')).limit(
        params.get('limit')).all()


def _get_labbooks_from_user(db: Session, params, user):
    logger.info(user.username)
    # TODO filter with roles in realm_access from user
    order_params = db_ordering.get_order_params(ordering=params.get('ordering'))
    if order_params:
        order_text = f'labbook.{order_params}'
    else:
        order_text = ''
    labbooks = db.query(models.Labbook).join(models.Group,
                                             models.Group.groupname == models.Labbook.title).join(
        models.UserToGroupRole,
        models.Group.id == models.UserToGroupRole.group_id).join(
        models.User, models.UserToGroupRole.user_id == models.User.id).filter(
        models.Labbook.deleted == bool(params.get('deleted'))).filter(
        models.User.username == user.username).order_by(
        text(order_text)).offset(params.get('offset')).limit(
        params.get('limit')).all()
    return labbooks


def create_labbook(db: Session, labbook: LabbookCreate):
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
    db_lb = db.query(models.Labbook).join(models.Group,
                                          models.Group.groupname == models.Labbook.title).filter(
        models.Labbook.id == labbook_pk).first()
    if db_lb:
        user_roles = get_user_group_roles(db=db,
                                          username=user.username,
                                          groupname=db_lb.title)

        privileges = create_labbook_privileges(user_roles=user_roles)

        return {'privileges': privileges, 'labbook': db_lb}

    return {'privileges': None, 'labbook': None}


def patch_labbook(db: Session, labbook_pk, labbook: LabbookPatch):
    db_labbook = db.query(models.Labbook).get(labbook_pk)
    db_labbook.title = labbook.title
    db_labbook.last_modified_at = datetime.datetime.now()
    db_labbook.last_modified_by_id = FAKE_USER_ID
    try:
        db.commit()
    except SQLAlchemyError as e:
        logger.error(e)
    db.refresh(db_labbook)
    # try:
    #     transmit({'model_name': 'labbook', 'model_pk': str(labbook_pk)})
    # except RuntimeError as e:
    #     print(e)

    return db_labbook


def get_labbook_export_link(db: Session, labbook_pk):
    db_labbook = db.query(models.Labbook).get(labbook_pk)
    db_labbook = build_labbook_download_url_with_token(lb_to_process=db_labbook,
                                                       user='foo')
    export_link = {
        'url': db_labbook.path,
        'filename': db_labbook.title
    }

    return export_link


def build_labbook_download_url_with_token(lb_to_process, user):
    user = security._authenticate_user(security.fake_users_db, 'johndoe',
                                       'secret')
    access_token_expires = security.timedelta(
        minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    lb_to_process.path = f'{URL_BASE_PATH}labbooks/{lb_to_process.id}/export?jwt={security.Token(access_token=access_token, token_type="bearer").access_token}'
    return lb_to_process
