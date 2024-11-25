from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from joeseln_backend.models import models
from joeseln_backend.services.user.user_schema import *
from joeseln_backend.mylogging.root_logger import logger


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
        db_user.groups = oidc_user.realm_access['roles']
        return db_user
    elif db_user.email != oidc_user.email:
        db_user.email = oidc_user.email
        try:
            db.commit()
        except SQLAlchemyError as e:
            logger.error(e)
            db.close()
            return db_user

        db.refresh(db_user)
        db_user.groups = oidc_user.realm_access['roles']
        return db_user
    else:
        db_user.groups = oidc_user.realm_access['roles']
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
        db_user.username = user_to_patch.username
        db_user.first_name = user_to_patch.first_name
        db_user.last_name = user_to_patch.last_name
        db_user.email = user_to_patch.user_email
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


def guicreate_user(db: Session, user, user_to_create: GuiUserCreate):
    if user.admin and (
            user_to_create.password == user_to_create.password_confirmed):

        db_user = models.User(username=user_to_create.username,
                              email=user_to_create.email,
                              password=user_to_create.password,
                              first_name=user_to_create.first_name,
                              last_name=user_to_create.last_name,
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
