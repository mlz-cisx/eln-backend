from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from joeseln_backend.models import models
from joeseln_backend.services.comment.comment_schemas import *
from joeseln_backend.conf.mocks.mock_user import FAKE_USER_ID
from joeseln_backend.conf.content_types import type2model, comment_content_type, \
    comment_content_type_model
from joeseln_backend.mylogging.root_logger import logger


def create_comment(db: Session, comment: CreateComment):
    db_comment = models.Comment(
        content=comment.content,
        version_number=0,
        created_at=datetime.datetime.now(),
        created_by_id=FAKE_USER_ID,
        last_modified_at=datetime.datetime.now(),
        last_modified_by_id=FAKE_USER_ID)
    db.add(db_comment)
    try:
        db.commit()
    except SQLAlchemyError as e:
        logger.error(e)
    db.refresh(db_comment)

    db_relation = models.Relation(
        left_object_id=db_comment.id,
        right_object_id=comment.relates_to_pk,
        private=comment.private,
        left_content_type=comment_content_type,
        left_content_type_model=comment_content_type_model,
        right_content_type=comment.relates_to_content_type_id,
        right_content_type_model=type2model[comment.relates_to_content_type_id],
        created_at=datetime.datetime.now(),
        created_by_id=FAKE_USER_ID,
        last_modified_at=datetime.datetime.now(),
        last_modified_by_id=FAKE_USER_ID,
        version_number=0
    )

    db.add(db_relation)
    try:
        db.commit()
    except SQLAlchemyError as e:
        logger.error(e)
    db.refresh(db_relation)

    return db_comment
