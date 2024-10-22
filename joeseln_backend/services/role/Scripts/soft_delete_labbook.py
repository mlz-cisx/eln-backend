import sys

sys.path.insert(0, '../../../..')

from joeseln_backend.database.database import SessionLocal
from joeseln_backend.services.labbook.labbook_service import soft_delete_labbook


def labbook_soft_deleter():
    print('----- Here you can soft delete a labbook ------')
    labbook_title = input("Enter labbook_name:")
    my_session = SessionLocal()
    if soft_delete_labbook(db=my_session, labbook_title=labbook_title,
                           username='admin'):
        print(f'Labbook {labbook_title} successfully soft deleted!')
    else:
        print(f'Labbook {labbook_title} could not be soft deleted!')


if __name__ == "__main__":
    labbook_soft_deleter()
