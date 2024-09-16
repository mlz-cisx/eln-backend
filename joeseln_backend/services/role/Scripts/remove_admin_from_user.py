from joeseln_backend.services.user_to_group.user_to_group_service import \
    remove_admin_role
from joeseln_backend.database.database import SessionLocal


def admin_remover():
    print('----- Here you can remove admin role from User ------')
    username = input("Enter Username:")
    my_session = SessionLocal()
    if remove_admin_role(db=my_session, username=username):
        print(f'admin role removed from {username}')
    else:
        print(f'admin role could not be removed from user with name {username}')


if __name__ == "__main__":
    admin_remover()
