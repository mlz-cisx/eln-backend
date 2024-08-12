from joeseln_backend.database.database import SessionLocal
from joeseln_backend.services.user_to_group.user_to_group_service import \
    create_group, create_user_to_group, get_user_group_roles, \
    get_user_group_roles, get_user_groups, check_for_admin_role
from joeseln_backend.services.user_to_group.user_to_group_schema import Group, \
    UserToGroup_Create
from joeseln_backend.conf.mocks.mock_user_to_group import TEST_USER_TO_GROUP

from joeseln_backend.services.labbook.labbook_service import \
    _get_labbooks_from_user

my_session = SessionLocal()

# test_group = create_group(db=my_session, groupname='test_group_4')
# print(Group.parse_obj(test_group))

# test_user_to_group = create_user_to_group(db=my_session,
#                                           user_to_group=UserToGroup_Create.parse_obj(
#                                               TEST_USER_TO_GROUP))
# print(UserToGroup_Create.parse_obj(test_user_to_group))


user_roles = get_user_group_roles(db=my_session,
                                  username='wb_test_1',
                                  groupname='test_group_4')

print(user_roles)

groups = get_user_groups(db=my_session,
                         username='user1')

for group in groups:
    user_roles = get_user_group_roles(db=my_session,
                                      username='wb_test_1',
                                      groupname=group)
    for role in user_roles:
        print(f'{role[0]} in {group}')

admin_role = check_for_admin_role(db=my_session, username='wb_test_1')
print(admin_role)
