from joeseln_backend.database.database import SessionLocal
from joeseln_backend.services.user_to_group.user_to_group_service import \
    create_group, create_user_to_group, get_user_group_roles, \
    get_user_group_roles, get_user_groups
from joeseln_backend.services.user_to_group.user_to_group_schema import Group, \
    UserToGroup_Create
from joeseln_backend.conf.mocks.mock_user_to_group import TEST_USER_TO_GROUP

my_session = SessionLocal()

# test_group = create_group(db=my_session, groupname='test_group_4')
# print(Group.parse_obj(test_group))

# test_user_to_group = create_user_to_group(db=my_session, user_to_group=UserToGroup_Create.parse_obj(TEST_USER_TO_GROUP))
# print(UserToGroup_Create.parse_obj(test_user_to_group))


user_roles = get_user_group_roles(db=my_session,
                                  username='user1',
                                  groupname='test_group_3')

for role in user_roles:
    print(role.rolename)

groups = get_user_groups(db=my_session,
                         username='user1')

print(groups)
