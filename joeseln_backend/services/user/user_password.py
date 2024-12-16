import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from joeseln_backend.auth.security import get_password_hash
from joeseln_backend.models import models
from joeseln_backend.mylogging.root_logger import logger
from joeseln_backend.services.user import user_schema
from joeseln_backend.conf.base_conf import INITIAL_ADMIN, INSTRUMENT_AS_ADMIN
from joeseln_backend.services.user.user_schema import GuiUserCreate


def change_user_password(db: Session, username, hashed_password):
    db_user = db.query(models.User).filter_by(username=username).first()
    if db_user:
        db_user.password = hashed_password
        try:
            db.commit()
        except SQLAlchemyError as e:
            logger.error(e)
            db.close()
            return
        db.refresh(db_user)
        return db_user
    return


def gui_password_change(db: Session, user,
                        none_hashed_password: user_schema.PasswordChange):
    db_user = db.query(models.User).get(user.id)
    if db_user and not db_user.oidc_user:
        db_user.password = get_password_hash(
            none_hashed_password.password.strip())
        try:
            db.commit()
        except SQLAlchemyError as e:
            logger.error(e)
            db.close()
            return
        db.refresh(db_user)
        return db_user
    return


def gui_patch_user_password(db: Session, authed_user, user_id,
                            password_to_patch: user_schema.PasswordPatch):
    if authed_user.admin:
        db_user = db.query(models.User).get(user_id)
        if db_user and not db_user.oidc_user and db_user.username not in [
            INITIAL_ADMIN, INSTRUMENT_AS_ADMIN]:
            db_user.password = get_password_hash(
                password_to_patch.password_patch.strip())
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


def guicreate_user(db: Session, user, user_to_create: GuiUserCreate):
    if user.admin and (
            user_to_create.password == user_to_create.password_confirmed):

        db_user = models.User(username=user_to_create.username.strip(),
                              email=user_to_create.email.strip(),
                              password=get_password_hash(
                                  user_to_create.password.strip()),
                              first_name=user_to_create.first_name.strip(),
                              last_name=user_to_create.last_name.strip(),
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
    return
