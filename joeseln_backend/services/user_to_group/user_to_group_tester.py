from joeseln_backend.database.database import SessionLocal
from joeseln_backend.services.user_to_group.user_to_group_service import create_group, create_user_to_group
from joeseln_backend.services.user_to_group.user_to_group_schema import GetGroup, UserToGroup_Create
from joeseln_backend.conf.mocks.mock_user_to_group import TEST_USER_TO_GROUP

my_session = SessionLocal()

# test_group = create_group(db=my_session, groupname='test_group_3')
# print(GetGroup.parse_obj(test_group))


test_user_to_group = create_user_to_group(db=my_session, user_to_group=UserToGroup_Create.parse_obj(TEST_USER_TO_GROUP))
print(UserToGroup_Create.parse_obj(test_user_to_group))