import datetime

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from joeseln_backend.conf.base_conf import INITIAL_ADMIN, INSTRUMENT_AS_ADMIN
from joeseln_backend.models import models
from joeseln_backend.mylogging.root_logger import logger
from joeseln_backend.services.user.user_schema import (
    GuiUserPatch,
    OIDCUserCreate,
    UserCreate,
)


def get_user_by_uname(db: Session, username):
    return db.query(models.User).filter_by(username=username).first()


def update_oidc_user(db: Session, oidc_user: OIDCUserCreate):
    db_user = get_user_by_uname(db=db, username=oidc_user.preferred_username)
    if not db_user:
        db_user = models.User(username=oidc_user.preferred_username,
                              email=oidc_user.email,
                              oidc_user=True,
                              first_name=oidc_user.given_name,
                              last_name=oidc_user.family_name,
                              created_at=datetime.datetime.now(),
                              last_modified_at=datetime.datetime.now()
                              )

        try:
            db.add(db_user)
            db.commit()
        except SQLAlchemyError as e:
            logger.error(e)
            db.close()
            return
        db.refresh(db_user)
        try:
            db_user.groups = oidc_user.realm_access['roles']
        except TypeError:
            db_user.groups = []
        return db_user
    elif db_user.email != oidc_user.email or \
            db_user.first_name != oidc_user.given_name or \
            db_user.last_name != oidc_user.family_name:
        db_user.email = oidc_user.email
        db_user.first_name = oidc_user.given_name
        db_user.last_name = oidc_user.family_name
        try:
            db.commit()
        except SQLAlchemyError as e:
            logger.error(e)
            db.close()
            return db_user
        db.refresh(db_user)
        try:
            db_user.groups = oidc_user.realm_access['roles']
        except TypeError as e:
            logger.error(str(e))
            db_user.groups = []
        return db_user
    else:
        try:
            db_user.groups = oidc_user.realm_access['roles']
        except TypeError:
            db_user.groups = []
        return db_user


def create_user(db: Session, user: UserCreate):
    db_user = models.User(username=user.username,
                          email=user.email,
                          oidc_user=user.oidc_user,
                          password=user.password,
                          first_name=user.first_name,
                          last_name=user.last_name,
                          created_at=datetime.datetime.now(),
                          last_modified_at=datetime.datetime.now()
                          )

    try:
        db.add(db_user)
        db.commit()
    except SQLAlchemyError as e:
        logger.error(e)
        db.close()
        return
    db.refresh(db_user)
    return db_user


def create_admin(db: Session, user: UserCreate):
    db_user = models.User(username=user.username,
                          email=user.email,
                          oidc_user=user.oidc_user,
                          admin=True,
                          password=user.password,
                          first_name=user.first_name,
                          last_name=user.last_name,
                          created_at=datetime.datetime.now(),
                          last_modified_at=datetime.datetime.now()
                          )

    try:
        db.add(db_user)
        db.commit()
    except SQLAlchemyError as e:
        logger.error(e)
        db.close()
        return
    db.refresh(db_user)
    return db_user


def gui_patch_user(db: Session, authed_user, user_id,
                   user_to_patch: GuiUserPatch):
    if authed_user.admin:
        db_user = db.query(models.User).get(user_id)
        if db_user.username not in [INITIAL_ADMIN, INSTRUMENT_AS_ADMIN]:
            db_user.username = user_to_patch.username.strip()
            db_user.first_name = user_to_patch.first_name.strip()
            db_user.last_name = user_to_patch.last_name.strip()
            db_user.email = user_to_patch.user_email.strip()
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
