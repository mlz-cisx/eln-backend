from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import text

from joeseln_backend.models import models
from joeseln_backend.services.labbook.labbook_schemas import *
from joeseln_backend.auth import security
from joeseln_backend.helper import db_ordering
from joeseln_backend.conf.base_conf import URL_BASE_PATH
from joeseln_backend.conf.mocks.mock_user import FAKE_USER_ID

from joeseln_backend.mylogging.root_logger import logger


def get_labbooks(db: Session, params):
    # print(params.get('ordering'))
    order_params = db_ordering.get_order_params(ordering=params.get('ordering'))
    return db.query(models.Labbook).filter_by(
        deleted=bool(params.get('deleted'))).order_by(
        text(order_params)).offset(params.get('offset')).limit(
        params.get('limit')).all()


def create_labbook(db: Session, labbook: LabbookCreate):
    db_labbook = models.Labbook(version_number=0,
                                title=labbook.title,
                                description=labbook.description,
                                created_at=datetime.datetime.now(),
                                created_by_id=FAKE_USER_ID,
                                last_modified_at=datetime.datetime.now(),
                                last_modified_by_id=FAKE_USER_ID)
    db.add(db_labbook)
    db.commit()
    db.refresh(db_labbook)
    return db_labbook


def get_labbook(db: Session, labbook_pk):
    return db.query(models.Labbook).get(labbook_pk)


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
    user = security.authenticate_user(security.fake_users_db, 'johndoe',
                                      'secret')
    access_token_expires = security.timedelta(
        minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    lb_to_process.path = f'{URL_BASE_PATH}labbooks/{lb_to_process.id}/export?jwt={security.Token(access_token=access_token, token_type="bearer").access_token}'
    return lb_to_process
