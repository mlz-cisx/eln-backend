from joeseln_backend.services.user_to_group.user_to_group_service import \
    add_admin_role
from joeseln_backend.database.database import SessionLocal


def admin_creator():
    print('----- Here you can add admin role to User ------')
    username = input("Enter Username:")
    my_session = SessionLocal()
    if add_admin_role(db=my_session, username=username):
        print(f'admin role added to {username}')
    else:
        print(f'admin role could not be added to user with name {username}')


if __name__ == "__main__":
    admin_creator()
