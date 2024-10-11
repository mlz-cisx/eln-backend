import sys

sys.path.insert(0, '../../../..')
from joeseln_backend.auth.security import get_password_hash
from joeseln_backend.services.user.user_service import \
    change_user_password
from joeseln_backend.database.database import SessionLocal


def user_updater():
    print('----- Here you can change user password ------')
    username = input("Enter username:")
    password = input("Enter password:")

    my_session = SessionLocal()
    if change_user_password(db=my_session, username=username,
                            hashed_password=get_password_hash(password)):
        print(f'password from {username} updated')
    else:
        print(f'password from {username} could not be updated')


if __name__ == "__main__":
    user_updater()
