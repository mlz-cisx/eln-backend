import sys

sys.path.insert(0, '../../../..')
from joeseln_backend.database.database import SessionLocal
from joeseln_backend.services.user_to_group.user_to_group_service import create_group


def group_creator():
    print('----- Here you can create a group ------')
    groupname = input("Enter Groupname:")
    my_session = SessionLocal()
    if create_group(db=my_session, groupname=groupname):
        print(f'group {groupname} created')
    else:
        print(f'group {groupname} could not be created')


if __name__ == "__main__":
    group_creator()
