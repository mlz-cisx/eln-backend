from joeseln_backend.conf.mocks.mock_user import TEST_USER_2
from joeseln_backend.database.database import SessionLocal
from joeseln_backend.services.user.user_service import create_user
from joeseln_backend.services.user.user_schema import UserExtended, UserCreate

my_session = SessionLocal()

test_user = create_user(db=my_session, user=UserCreate.parse_obj(TEST_USER_2))
print(UserExtended.parse_obj(test_user))

# test_user = get_user_by_uname(db=my_session, username='user2')
# print(verify_password('secret', UserExtended.parse_obj(test_user).password))

