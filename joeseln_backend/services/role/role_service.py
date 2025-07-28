import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from joeseln_backend.models import models
from joeseln_backend.services.role.role_schema import Role_Create
from joeseln_backend.mylogging.root_logger import logger


def get_role_by_rolename(db: Session, rolename):
    return db.query(models.Role).filter_by(rolename=rolename).first()


def create_role(db: Session, role: Role_Create):
    db_role = models.Role(rolename=role.rolename,
                          description=role.description,
                          created_at=datetime.datetime.now(),
                          last_modified_at=datetime.datetime.now()
                          )

    try:
        db.add(db_role)
        db.commit()
    except SQLAlchemyError as e:
        logger.error(e)
        db.close()
        return
    db.refresh(db_role)
    return db_role
