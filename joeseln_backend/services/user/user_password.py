from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from joeseln_backend.auth.security import get_password_hash
from joeseln_backend.models import models
from joeseln_backend.mylogging.root_logger import logger
from joeseln_backend.services.user import user_schema


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
    if db_user:
        db_user.password = get_password_hash(none_hashed_password.password)
        try:
            db.commit()
        except SQLAlchemyError as e:
            logger.error(e)
            db.close()
            return
        db.refresh(db_user)
        return db_user
    return
