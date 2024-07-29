from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from joeseln_backend.models import models
from joeseln_backend.services.user.user_schema import *
from joeseln_backend.mylogging.root_logger import logger


def get_user_by_uname(db: Session, username):
    return db.query(models.User).filter_by(username=username).first()


def update_oidc_user(db: Session, oidc_user: OIDC_User_Create):
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
            return
        db.refresh(db_user)
        return oidc_user
    elif db_user.email != oidc_user.email:
        db_user.email = oidc_user.email
        try:
            db.commit()
        except SQLAlchemyError as e:
            logger.error(e)

        db.refresh(db_user)
        return oidc_user
    else:
        return oidc_user


def create_user(db: Session, user: User_Create):
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
        return
    db.refresh(db_user)
    return db_user
