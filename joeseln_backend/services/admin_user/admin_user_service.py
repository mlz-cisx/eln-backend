import datetime

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from sqlalchemy import or_

from joeseln_backend.mylogging.root_logger import logger
from joeseln_backend.services.privileges.admin_privileges.privileges_service import \
    ADMIN

from joeseln_backend.helper import db_ordering
from joeseln_backend.models import models


def _get_all_users(db: Session, params, user):
    order_params = db_ordering.get_order_params(ordering=params.get('ordering'))

    if user.admin:
        if params.get('search'):
            search_text = params.get('search')
            users = db.query(models.User).filter(
                models.User.username.ilike(f'%{search_text}%')).order_by(
                text(order_params)).offset(params.get('offset')).limit(
                params.get('limit')).all()
        else:
            users = db.query(models.User).order_by(
                text(order_params)).offset(params.get('offset')).limit(
                params.get('limit')).all()

        return users
    return


def get_all_users(db: Session, params, user):
    order_params = db_ordering.get_order_params(ordering=params.get('ordering'))

    if user.admin:
        if params.get('search'):
            search_text = params.get('search')
            users = db.query(models.User).filter(or_(
                models.User.username.ilike(f'%{search_text}%'),
                models.User.first_name.ilike(f'%{search_text}%'),
                models.User.last_name.ilike(f'%{search_text}%'),
            )).filter_by(
                deleted=bool(params.get('deleted'))).order_by(
                text(order_params)).offset(params.get('offset')).limit(
                params.get('limit')).all()
        else:
            users = db.query(models.User).filter_by(
                deleted=bool(params.get('deleted'))).order_by(
                text(order_params)).offset(params.get('offset')).limit(
                params.get('limit')).all()

        return users
    return


def soft_delete_user(db: Session, user_id, user):
    if user.admin:
        db_user = db.query(models.User).get(user_id)
        if db_user and not db_user.deleted:
            db_user.deleted = True
            db_user.last_modified_at = datetime.datetime.now()
            try:
                db.commit()
            except SQLAlchemyError as e:
                logger.error(e)
                db.close()
                return
            db.refresh(db_user)
            return db_user
        return
    return


def restore_user(db: Session, user_id, user):
    if user.admin:
        db_user = db.query(models.User).get(user_id)
        if db_user and db_user.deleted:
            db_user.deleted = False
            db_user.last_modified_at = datetime.datetime.now()
            try:
                db.commit()
            except SQLAlchemyError as e:
                logger.error(e)
                db.close()
                return
            db.refresh(db_user)
            return db_user
        return
    return


def get_user_by_id(db: Session, user, user_id):
    if user.admin:
        db_user = db.query(models.User).get(user_id)
        return {'privileges': ADMIN, 'user': db_user}
    return
