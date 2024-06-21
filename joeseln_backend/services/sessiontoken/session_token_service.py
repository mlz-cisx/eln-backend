from datetime import datetime, timedelta, timezone
from sqlalchemy.exc import SQLAlchemyError

from joeseln_backend.database.database import SessionLocal
from joeseln_backend.models import models

from joeseln_backend.mylogging.root_logger import logger


class TokenService:
    @staticmethod
    def set_token_exp(token, exp):
        # print('token set ', exp)
        db = SessionLocal()
        sessiontoken = models.SessionToken(token=token,
                                           expiration_time=exp + 10)
        db.add(sessiontoken)
        db.commit()
        db.refresh(sessiontoken)
        db.close()
        return sessiontoken

    @staticmethod
    def get_token_exp(token):
        db = SessionLocal()
        sessiontoken = db.query(models.SessionToken).filter_by(
            token=token).first()
        db.close()
        return sessiontoken.expiration_time

    @staticmethod
    def extend_token(token):
        db = SessionLocal()
        sessiontoken = db.query(models.SessionToken).filter_by(
            token=token).first()
        sessiontoken.expiration_time = int(
            (datetime.now(timezone.utc) + timedelta(seconds=1000)).strftime(
                "%Y%m%d%H%M%S"))
        try:
            db.commit()
        except SQLAlchemyError as e:
            logger.error(e)
            return False
        db.refresh(sessiontoken)
        db.close()
        return True
