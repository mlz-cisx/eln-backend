from joeseln_backend.services.user_to_group.user_to_group_service import \
    add_as_user_to_group
from joeseln_backend.database.database import SessionLocal


def user_creator():
    print('----- Here you can add user role to User ------')
    username = input("Enter Username:")
    groupname = input("Enter Groupname:")
    my_session = SessionLocal()
    if add_as_user_to_group(db=my_session, username=username,
                            groupname=groupname):
        print(f'user role added to {username} in {groupname}')
    else:
        print(
            f'user role could not be added to user {username} in {groupname}')


if __name__ == "__main__":
    user_creator()
