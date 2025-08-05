import sys

sys.path.insert(0, '../../../..')

from joeseln_backend.database.database import SessionLocal
from joeseln_backend.services.labbook.labbook_service import (
    get_non_deleted_labbooks,
    soft_delete_labbook,
)


def labbook_soft_deleter():
    print('----- Here you can soft delete a labbook ------')
    my_session = SessionLocal()
    print('----- All non deleted labbooks: ------')
    lbs = get_non_deleted_labbooks(db=my_session)
    for lb in lbs:
        print(f'{lb.id}    {lb.title}')
    print('')
    labbook_uuid = input("Enter labbook uuid:")
    if soft_delete_labbook(db=my_session, labbook_uuid=labbook_uuid,
                           username='admin'):
        print(f'Labbook {labbook_uuid} successfully soft deleted!')
    else:
        print(f'Labbook {labbook_uuid} could not be soft deleted!')


if __name__ == "__main__":
    labbook_soft_deleter()
