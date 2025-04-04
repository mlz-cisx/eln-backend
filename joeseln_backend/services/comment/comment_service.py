import sys

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from joeseln_backend.conf.base_conf import ELEM_MAXIMUM_SIZE
from joeseln_backend.models import models
from joeseln_backend.services.comment.comment_schemas import *
from joeseln_backend.conf.content_types import type2model, comment_content_type, \
    comment_content_type_model
from joeseln_backend.mylogging.root_logger import logger
from joeseln_backend.services.labbook.labbook_service import \
    check_for_labbook_access
from joeseln_backend.ws.ws_client import transmit


def create_comment(db: Session, comment: CreateComment, user):
    if sys.getsizeof(comment.content) > ELEM_MAXIMUM_SIZE << 10:
        return None

    if comment.relates_to_content_type_id == 30:
        db_note = db.query(models.Note).get(comment.relates_to_pk)
        lb_elem = db.query(models.Labbookchildelement).get(db_note.elem_id)

    elif comment.relates_to_content_type_id == 40:
        db_pic = db.query(models.Picture).get(comment.relates_to_pk)
        lb_elem = db.query(models.Labbookchildelement).get(db_pic.elem_id)

    elif comment.relates_to_content_type_id == 50:
        db_file = db.query(models.File).get(comment.relates_to_pk)
        lb_elem = db.query(models.Labbookchildelement).get(db_file.elem_id)
    else:
        return

    if check_for_labbook_access(db=db, labbook_pk=lb_elem.labbook_id,
                                user=user):

        db_comment = models.Comment(
            content=comment.content,
            version_number=0,
            created_at=datetime.datetime.now(),
            created_by_id=user.id,
            last_modified_at=datetime.datetime.now(),
            last_modified_by_id=user.id)
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
            right_content_type_model=type2model[
                comment.relates_to_content_type_id],
            created_at=datetime.datetime.now(),
            created_by_id=user.id,
            last_modified_at=datetime.datetime.now(),
            last_modified_by_id=user.id,
            version_number=0
        )

        db.add(db_relation)
        try:
            db.commit()
        except SQLAlchemyError as e:
            logger.error(e)
        db.refresh(db_relation)

        return db_comment
