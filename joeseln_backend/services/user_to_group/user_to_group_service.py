from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from joeseln_backend.models import models
from joeseln_backend.services.user.user_service import get_user_by_uname
from joeseln_backend.services.user_to_group.user_to_group_schema import *
from joeseln_backend.mylogging.root_logger import logger


def get_group_by_groupname(db: Session, groupname):
    return db.query(models.Group).filter_by(groupname=groupname).first()


def create_group(db: Session, groupname):
    db_group = models.Group(groupname=groupname,
                            created_at=datetime.datetime.now(),
                            last_modified_at=datetime.datetime.now()
                            )
    try:
        db.add(db_group)
        db.commit()
    except SQLAlchemyError as e:
        logger.error(e)
        return
    db.refresh(db_group)
    return db_group


def create_user_to_group(db: Session, user_to_group: UserToGroup_Create):
    db_group = models.UserToGroupRole(user_id=user_to_group.user_id,
                                      group_id=user_to_group.group_id,
                                      user_group_role=user_to_group.user_group_role,
                                      created_at=datetime.datetime.now(),
                                      last_modified_at=datetime.datetime.now()
                                      )
    try:
        db.add(db_group)
        db.commit()
    except SQLAlchemyError as e:
        logger.error(e)
        return
    db.refresh(db_group)
    return db_group


def get_user_group_roles(db: Session, username,
                         groupname):
    db_user = get_user_by_uname(db=db, username=username).first()
    db_group = get_group_by_groupname(db=db, groupname=groupname).first()
    group_roles = db.query(models.UserToGroupRole).filter_by(user_id=db_user.id,
                                                             group_id=db_group.id).all()
    return group_roles
