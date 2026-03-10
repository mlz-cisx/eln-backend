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
        connection.execute(
            text(
                """
            DO $$
            BEGIN
                -- if owner_group column not exist
                IF NOT EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name='labbook'
                    AND column_name='owner_group'
                ) THEN
                    -- create group if not exist
                    DECLARE
                    labbook_record RECORD;
                    BEGIN
                        FOR labbook_record IN SELECT title FROM labbook LOOP
                            IF NOT EXISTS (SELECT 1 FROM "group" WHERE groupname = labbook_record.title) THEN
                                -- insert the group if it doesn't exist
                                INSERT INTO "group" (id, groupname, created_at, last_modified_at)
                                VALUES (gen_random_uuid(), labbook_record.title, NOW(), NOW());
                            END IF;
                        END LOOP;
                    END;
                    -- create column and set it as labbook title
                    ALTER TABLE public.labbook
                        ADD COLUMN owner_group VARCHAR DEFAULT NULL;
                    UPDATE public.labbook
                        SET owner_group = title;
                END IF;
            END $$;
            """
            )
        )
        transaction.commit()
    except sqlalchemy.exc.ProgrammingError as e:
        logger.info(e)
        transaction.rollback()
    finally:
        connection.close()
