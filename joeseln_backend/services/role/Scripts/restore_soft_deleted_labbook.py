import sys

sys.path.insert(0, '../../../..')

from joeseln_backend.database.database import SessionLocal
from joeseln_backend.services.labbook.labbook_service import (
    get_deleted_labbooks,
    restore_labbook,
)


def labbook_restore():
    print('----- Here you can restore a soft deleted labbook ------')
    my_session = SessionLocal()
    print('----- All soft deleted labbooks: ------')
    lbs = get_deleted_labbooks(db=my_session)
    for lb in lbs:
        print(f'{lb.id}    {lb.title}')
    print('')
    labbook_uuid = input("Enter labbook uuid:")
    if restore_labbook(db=my_session, labbook_uuid=labbook_uuid,
                       username='admin'):
        print(f'Labbook {labbook_uuid} successfully restored!')
    else:
        print(f'Labbook {labbook_uuid} could not be restored!')


if __name__ == "__main__":
    labbook_restore()
