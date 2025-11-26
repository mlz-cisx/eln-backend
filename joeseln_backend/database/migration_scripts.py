import sqlalchemy
from sqlalchemy import text

from joeseln_backend.database.database import engine
from joeseln_backend.mylogging.root_logger import logger


def update_db_tables():
    connection = engine.connect()
    transaction = connection.begin()
    try:
        connection.execute(
            text("ALTER TABLE public.file DROP COLUMN IF EXISTS plot_data;")
        )
        connection.execute(
            text(
                "ALTER TABLE public.picture ADD IF NOT EXISTS canvas_content  TEXT  DEFAULT '';"
            )
        )
        transaction.commit()
    except sqlalchemy.exc.ProgrammingError as e:
        logger.info(e)
        transaction.rollback()
    finally:
        connection.close()
