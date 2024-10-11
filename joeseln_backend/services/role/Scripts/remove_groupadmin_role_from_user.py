import sys

sys.path.insert(0, '../../../..')
from joeseln_backend.services.user_to_group.user_to_group_service import \
    remove_as_groupadmin_from_group
from joeseln_backend.database.database import SessionLocal


def groupadmin_remover():
    print('----- Here you can remove groupadmin role from User ------')
    username = input("Enter Username:")
    groupname = input("Enter Groupname:")
    my_session = SessionLocal()
    if remove_as_groupadmin_from_group(db=my_session, username=username,
                                       groupname=groupname):
        print(f'groupadmin role removed from {username} in {groupname}')
    else:
        print(
            f'groupadmin role could not be removed from {username} in {groupname}')


if __name__ == "__main__":
    groupadmin_remover()
