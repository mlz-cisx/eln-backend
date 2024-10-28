import sys

from joeseln_backend.services.file.file_service import get_all_deleted_files, \
    remove_soft_deleted_file

sys.path.insert(0, '../../../..')

from joeseln_backend.database.database import SessionLocal


def file_remover():
    print('----- Here you can remove a file ------')
    my_session = SessionLocal()
    print('----- All soft deleted files: ------')

    files = get_all_deleted_files(db=my_session)
    for file in files:
        print(f'{file.id}    {file.display}')
    print('')
    file_pk = input("Enter file uuid :")
    if remove_soft_deleted_file(db=my_session, file_pk=file_pk):
        print('----- File successfully removed ------')
    else:
        print('----- File could not be removed ------')


if __name__ == "__main__":
    file_remover()
