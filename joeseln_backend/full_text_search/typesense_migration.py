from joeseln_backend.models import models
from joeseln_backend.database.database import SessionLocal
from joeseln_backend.full_text_search.typesense_service import create_typesense_client
from joeseln_backend.full_text_search.html_stripper import strip_html_and_binary
from joeseln_backend.services.note.note_service import get_note


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


typesense = create_typesense_client()
db = SessionLocal()

try:
    labbook_elems = db.query(models.Labbookchildelement).all()

    for elem in labbook_elems:
        if elem.child_object_content_type == 30:
            note = get_note(db=db, note_pk=elem.child_object_id)

            stripped_content = strip_html_and_binary(note.content)
            typesense.collections["notes"].documents.upsert(
                {
                    "id": str(note.id),
                    "elem_id": str(elem.id),
                    "subject": note.subject,
                    "content": stripped_content,
                    "last_modified_at": int(note.last_modified_at.timestamp()),
                    "labbook_id": str(elem.labbook_id),
                    "soft_delete": bool(note.deleted),
                }
            )

finally:
    db.close()
