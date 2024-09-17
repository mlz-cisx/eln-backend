from joeseln_backend.auth.security import get_password_hash
from joeseln_backend.services.user.user_schema import User_Create
from joeseln_backend.services.user.user_service import \
    create_user
from joeseln_backend.database.database import SessionLocal


def user_creator():
    print('----- Here you can create a non oidc user ------')
    username = input("Enter username:")
    email = input("Enter email:")
    firstname = input("Enter firstname:")
    lastname = input("Enter lastname:")
    password = input("Enter password:")

    user_to_create = {
        'username': username,
        'email': email,
        'oidc_user': False,
        'password': get_password_hash(password),
        'first_name': firstname,
        'last_name': lastname
    }

    my_session = SessionLocal()
    if create_user(db=my_session, user=User_Create.parse_obj(user_to_create)):
        print(f'user {username} created')
    else:
        print(f'user {username} could not be created')


if __name__ == "__main__":
    user_creator()
