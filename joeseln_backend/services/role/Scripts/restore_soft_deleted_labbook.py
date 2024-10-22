import sys

sys.path.insert(0, '../../../..')

from joeseln_backend.database.database import SessionLocal
from joeseln_backend.services.labbook.labbook_service import restore_labbook


def labbook_restore():
    print('----- Here you can restore a soft deleted labbook ------')
    labbook_title = input("Enter labbook_name:")
    my_session = SessionLocal()
    if restore_labbook(db=my_session, labbook_title=labbook_title,
                       username='admin'):
        print(f'Labbook {labbook_title} successfully restored!')
    else:
        print(f'Labbook {labbook_title} could not be restored!')


if __name__ == "__main__":
    labbook_restore()
