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
        connection.execute(
            text(
                """
                DO $$
                DECLARE
                    constraint_exists BOOLEAN;
                BEGIN
                    SELECT EXISTS (
                        SELECT 1
                        FROM pg_constraint c
                        JOIN pg_class t ON c.conrelid = t.oid
                        JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(c.conkey)
                        WHERE t.relname = 'labbook'
                          AND a.attname = 'owner_group'
                          AND c.contype = 'u'   -- 'u' = UNIQUE constraint
                    ) INTO constraint_exists;

                    IF NOT constraint_exists THEN
                        ALTER TABLE public.labbook
                            ADD CONSTRAINT labbook_owner_group_unique UNIQUE (owner_group);
                    END IF;
                END $$;
                """
            )
        )
        # 1) Temporarily enable ON DELETE CASCADE for all elem_id foreign keys
        connection.execute(text("""
            -- NOTE
            ALTER TABLE note
            DROP CONSTRAINT IF EXISTS note_elem_id_fkey;

            ALTER TABLE note
            ADD CONSTRAINT note_elem_id_fkey
            FOREIGN KEY (elem_id)
            REFERENCES labbookchildelement(id)
            ON DELETE CASCADE;

            -- PICTURE
            ALTER TABLE picture
            DROP CONSTRAINT IF EXISTS picture_elem_id_fkey;

            ALTER TABLE picture
            ADD CONSTRAINT picture_elem_id_fkey
            FOREIGN KEY (elem_id)
            REFERENCES labbookchildelement(id)
            ON DELETE CASCADE;

            -- FILE
            ALTER TABLE file
            DROP CONSTRAINT IF EXISTS file_elem_id_fkey;

            ALTER TABLE file
            ADD CONSTRAINT file_elem_id_fkey
            FOREIGN KEY (elem_id)
            REFERENCES labbookchildelement(id)
            ON DELETE CASCADE;
        """))

        # 2) Delete surplus LabbookChildElements (cascade applies only now)
        connection.execute(text("""
            WITH duplicates AS (
                SELECT child_object_id
                FROM labbookchildelement
                GROUP BY child_object_id
                HAVING COUNT(*) > 1
            ),
            survivors AS (
                SELECT DISTINCT ON (child_object_id)
                       id AS survivor_id,
                       child_object_id
                FROM labbookchildelement
                WHERE child_object_id IN (SELECT child_object_id FROM duplicates)
                ORDER BY child_object_id, id
            )
            DELETE FROM labbookchildelement l
            USING duplicates d
            WHERE l.child_object_id = d.child_object_id
              AND l.id NOT IN (SELECT survivor_id FROM survivors);
        """))

        # 3) Restore all foreign keys WITHOUT CASCADE
        connection.execute(text("""
            -- NOTE
            ALTER TABLE note
            DROP CONSTRAINT IF EXISTS note_elem_id_fkey;

            ALTER TABLE note
            ADD CONSTRAINT note_elem_id_fkey
            FOREIGN KEY (elem_id)
            REFERENCES labbookchildelement(id)
            ON DELETE RESTRICT;

            -- PICTURE
            ALTER TABLE picture
            DROP CONSTRAINT IF EXISTS picture_elem_id_fkey;

            ALTER TABLE picture
            ADD CONSTRAINT picture_elem_id_fkey
            FOREIGN KEY (elem_id)
            REFERENCES labbookchildelement(id)
            ON DELETE RESTRICT;

            -- FILE
            ALTER TABLE file
            DROP CONSTRAINT IF EXISTS file_elem_id_fkey;

            ALTER TABLE file
            ADD CONSTRAINT file_elem_id_fkey
            FOREIGN KEY (elem_id)
            REFERENCES labbookchildelement(id)
            ON DELETE RESTRICT;
        """))

        # 4) Add the unique constraint
        connection.execute(text("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'uq_child_object_id'
            ) THEN
                ALTER TABLE labbookchildelement
                ADD CONSTRAINT uq_child_object_id
                UNIQUE (child_object_id);
            END IF;
        END$$;
        """))

        transaction.commit()
    except sqlalchemy.exc.ProgrammingError as e:
        logger.info(e)
        transaction.rollback()
    finally:
        connection.close()
