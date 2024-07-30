from joeseln_backend.services.user.user_service import get_user_by_uname
from joeseln_backend.services.user_to_group.user_to_group_service import \
    get_group_by_groupname
from joeseln_backend.services.role.role_service import get_role_by_rolename
from joeseln_backend.database.database import SessionLocal

my_session = SessionLocal()

test_user = get_user_by_uname(db=my_session, username='user1')
test_group = get_group_by_groupname(db=my_session, groupname='test_group_3')
test_role = get_role_by_rolename(db=my_session, rolename='user')

TEST_USER_TO_GROUP = {
    'user_id': test_user.id,
    'group_id': test_group.id,
    'user_group_role': test_role.id
}
