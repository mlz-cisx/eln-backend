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
from joeseln_backend.conf.base_conf import INITIAL_ADMIN, INSTRUMENT_AS_ADMIN
from joeseln_backend.services.user_to_group.user_to_group_service import \
    get_user_groups, get_user_groups_role_groupadmin


def get_all_users(db: Session, params, user):
    order_params = db_ordering.get_order_params(ordering=params.get('ordering'))
    cleared_order_params = order_params if not order_params.startswith(
        'connected') else 'created_at asc'

    if user.admin:
        if params.get('search'):
            search_text = params.get('search')
            users = db.query(models.User).filter(or_(
                models.User.username.ilike(f'%{search_text}%'),
                models.User.first_name.ilike(f'%{search_text}%'),
                models.User.last_name.ilike(f'%{search_text}%'),
            )).filter_by(
                deleted=bool(params.get('deleted'))).filter_by(
                admin=False).order_by(
                text(cleared_order_params)).offset(params.get('offset')).limit(
                params.get('limit')).all()
        else:
            users = db.query(models.User).filter_by(
                deleted=bool(params.get('deleted'))).filter_by(
                admin=False).order_by(
                text(cleared_order_params)).offset(params.get('offset')).limit(
                params.get('limit')).all()

        for user in users:
            user.connected = False if not db.query(
                models.UserConnectedWs).filter_by(
                username=user.username).first() else \
                db.query(models.UserConnectedWs.connected).filter_by(
                    username=user.username).first()[0]

        if order_params == 'connected asc':
            users.sort(key=lambda x: x.connected, reverse=True)
        if order_params == 'connected desc':
            users.sort(key=lambda x: x.connected)
        return users
    return


def get_all_admins(db: Session, params, user):
    order_params = db_ordering.get_order_params(ordering=params.get('ordering'))

    if user.admin:
        if params.get('search'):
            search_text = params.get('search')
            users = db.query(models.User).filter(or_(
                models.User.username.ilike(f'%{search_text}%'),
                models.User.first_name.ilike(f'%{search_text}%'),
                models.User.last_name.ilike(f'%{search_text}%'),
            )).filter_by(
                admin=not bool(params.get('deleted'))).filter_by(
                oidc_user=False).order_by(
                text(order_params)).offset(params.get('offset')).limit(
                params.get('limit')).all()
        else:
            users = db.query(models.User).filter_by(
                admin=not bool(params.get('deleted'))).filter_by(
                oidc_user=False).order_by(
                text(order_params)).offset(params.get('offset')).limit(
                params.get('limit')).all()

        return users
    return


def soft_delete_user(db: Session, user_id, user):
    if user.admin:
        db_user = db.query(models.User).get(user_id)
        if db_user and not db_user.deleted:
            # remove all user group roles
            try:
                db.query(models.UserToGroupRole).filter(
                    models.UserToGroupRole.user_id == user_id).delete()
                db.commit()
            except SQLAlchemyError as e:
                logger.error(e)
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


def set_as_admin(db: Session, user_id, user):
    if user.admin:
        db_user = db.query(models.User).get(user_id)
        # you can't add admin role to oidc user
        if db_user and not db_user.admin and not db_user.oidc_user and user.id != db_user.id:
            db_user.admin = True
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


def remove_as_admin(db: Session, user_id, user):
    if user.admin:
        db_user = db.query(models.User).get(user_id)
        # you can't remove own admnin role
        if db_user and db_user.admin and db_user.username not in [INITIAL_ADMIN,
                                                                  INSTRUMENT_AS_ADMIN]:
            db_user.admin = False
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

        groups = get_user_groups(db=db, username=db_user.username)
        admin_groups = get_user_groups_role_groupadmin(db=db,
                                                       username=db_user.username)
        db_user.groups = groups
        db_user.admin_groups = admin_groups

        return {'privileges': ADMIN, 'user': db_user}
    return
