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
                """
                ALTER TABLE public.picture 
                   ADD COLUMN IF NOT EXISTS canvas_content TEXT 
                   DEFAULT '{"version":"6.9.0","objects":[],"background":"#F8F8FF"}';
                   """
            )
        )
        connection.execute(
            text(
                """
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_schema = 'public'
                          AND table_name = 'picture'
                          AND column_name = 'canvas_content'
                    ) THEN
                        UPDATE public.picture
                        SET canvas_content = '{"version":"6.9.0","objects":[],"background":"#F8F8FF"}'
                        WHERE canvas_content = '';
                    END IF;
                END$$;
                """
            )
        )
        transaction.commit()
    except sqlalchemy.exc.ProgrammingError as e:
        logger.info(e)
        transaction.rollback()
    finally:
        connection.close()
