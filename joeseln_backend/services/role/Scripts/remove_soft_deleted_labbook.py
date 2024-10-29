import sys

sys.path.insert(0, '../../../..')

from joeseln_backend.database.database import SessionLocal
from joeseln_backend.services.labbook.labbook_service import \
    get_deleted_labbooks, remove_deleted_labbook_with_its_content


def labbook_remove():
    print('----- Here you can remove a soft deleted labbook ------')
    my_session = SessionLocal()
    print('----- All soft deleted labbooks: ------')
    lbs = get_deleted_labbooks(db=my_session)
    for lb in lbs:
        print(f'{lb.id}    {lb.title}')
    print('')

    labbook_uuid = input("Enter labbook uuid :")
    if remove_deleted_labbook_with_its_content(db=my_session,
                                               labbook_uuid=labbook_uuid):
        print('----- Labbook successfully removed ------')
    else:
        print('----- Labbook could not be removed ------')


if __name__ == "__main__":
    labbook_remove()
