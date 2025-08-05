import sys

from joeseln_backend.services.picture.picture_service import (
    get_all_deleted_pics,
    remove_soft_deleted_picture,
)

sys.path.insert(0, '../../../..')

from joeseln_backend.database.database import SessionLocal


def picture_remover():
    print('----- Here you can remove a picture ------')
    my_session = SessionLocal()
    print('----- All soft deleted pictures: ------')

    pics = get_all_deleted_pics(db=my_session)
    for pic in pics:
        print(f'{pic.id}    {pic.title}')
    print('')
    pic_pk = input("Enter picture uuid :")

    if remove_soft_deleted_picture(db=my_session, picture_pk=pic_pk):
        print('----- Picture successfully removed ------')
    else:
        print('----- Picture could not be removed ------')


if __name__ == "__main__":
    picture_remover()
