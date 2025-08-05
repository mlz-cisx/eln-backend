import sys

sys.path.insert(0, '../../../..')
from joeseln_backend.database.database import SessionLocal
from joeseln_backend.services.user_to_group.user_to_group_service import (
    remove_admin_role,
)


def admin_remover():
    print('----- Here you can remove admin role from User ------')
    username = input("Enter Username:")
    my_session = SessionLocal()
    if remove_admin_role(db=my_session, username=username):
        print(f'admin role removed from {username}')
    else:
        print(f'admin role could not be removed from {username}')


if __name__ == "__main__":
    admin_remover()
