import sys

sys.path.insert(0, '../../../..')

from joeseln_backend.database.database import SessionLocal
from joeseln_backend.services.note.note_service import get_all_deleted_notes, \
    remove_soft_deleted_note


def note_remover():
    print('----- Here you can remove a note ------')
    my_session = SessionLocal()
    print('----- All soft deleted notes: ------')
    notes = get_all_deleted_notes(db=my_session)
    for note in notes:
        print(f'{note.id}    {note.subject}')
    print('')
    note_pk = input("Enter note uuid :")
    if remove_soft_deleted_note(db=my_session, note_pk=note_pk):
        print('----- Note successfully removed ------')
    else:
        print('----- Note could not be removed ------')


if __name__ == "__main__":
    note_remover()
