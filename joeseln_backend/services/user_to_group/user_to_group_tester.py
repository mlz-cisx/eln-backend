from joeseln_backend.database.database import SessionLocal
from joeseln_backend.services.user_to_group.user_to_group_service import \
    create_group, create_user_to_group, get_user_group_roles, get_user_groups, \
    check_for_admin_role, remove_all_group_roles, \
    remove_as_groupadmin_from_group, remove_as_user_from_group, \
    get_user_groups_role_user, get_user_groups_role_groupadmin, \
    remove_admin_role, add_admin_role, add_as_groupadmin_to_group
from joeseln_backend.services.user_to_group.user_to_group_schema import Group, \
    UserToGroup_Create

my_session = SessionLocal()

# test_group = create_group(db=my_session, groupname='test_group_4')
# print(Group.parse_obj(test_group))

# user_roles = get_user_group_roles(db=my_session,
#                                   username='wb_test_1',
#                                   groupname='test_group_4')

# print(user_roles)

# groups = get_user_groups(db=my_session,
#                          username='admin')
#
# for group in groups:
#     user_roles = get_user_group_roles(db=my_session,
#                                       username='admin',
#                                       groupname=group)
#     for role in user_roles:
#         print(f'{role[0]} in {group}')
#
# remove_admin_role(db=my_session, username='wb_test_1')
#
# print(check_for_admin_role(db=my_session, username='wb_test_1'))

# add_admin_role(db=my_session, username='wb_test_1')

# print(check_for_admin_role(db=my_session, username='wb_test_1'))


# remove_all_group_roles(db=my_session, username='wb_test_1',
#                        groupname='test_group_3')
#
# remove_as_user_from_group(db=my_session, username='user1',
#                           groupname='test_group_3')
#
# print(get_user_groups_role_groupadmin(db=my_session, username='admin'))


# lbs = get_user_groups_role_groupadmin(db=my_session, username='wb_test_1')
# print(lbs)
# add_as_groupadmin_to_group(db=my_session,username='wb_test_1', groupname='test1')
# lbs = get_user_groups_role_groupadmin(db=my_session, username='wb_test_1')
# print(lbs)
# remove_as_groupadmin_from_group(db=my_session,username='wb_test_1', groupname='test1')
lbs = get_user_groups_role_groupadmin(db=my_session, username='wb_test_1')
print(lbs)