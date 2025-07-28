import sqlalchemy
from sqlalchemy import text
from joeseln_backend.database.database import engine
from joeseln_backend.mylogging.root_logger import logger


def update_db_tables():
    connection = engine.connect(close_with_result=True)
    try:
        connection.execute(text("ALTER TABLE public.file ADD IF NOT EXISTS plot_data  TEXT  DEFAULT '[]';"))
    except sqlalchemy.exc.ProgrammingError as e:
        logger.info(e)


