import sys

sys.path.insert(0, '../../../..')
from joeseln_backend.database.database import SessionLocal
from joeseln_backend.services.user_to_group.user_to_group_service import (
    remove_as_user_from_group,
)


def user_remover():
    print('----- Here you can remove user role from User ------')
    username = input("Enter Username:")
    groupname = input("Enter Groupname:")
    my_session = SessionLocal()
    if remove_as_user_from_group(db=my_session, username=username,
                                 groupname=groupname):
        print(f'user role removed from {username} in {groupname}')
    else:
        print(
            f'user role could not be removed from {username} in {groupname}')


if __name__ == "__main__":
    user_remover()
