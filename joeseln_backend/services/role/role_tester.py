from joeseln_backend.conf.mocks.mock_role import ROLE_USER, ROLE_ADMIN, ROLE_GROUPADMIN
from joeseln_backend.database.database import SessionLocal
from joeseln_backend.services.role.role_service import create_role, \
    get_role_by_rolename
from joeseln_backend.services.role.role_schema import *
from joeseln_backend.auth.security import verify_password

my_session = SessionLocal()

# test_role = create_role(db=my_session, role=Role_Create.parse_obj(ROLE_GROUPADMIN))
test_role = get_role_by_rolename(db=my_session, rolename='groupadmin')
print(Role.parse_obj(test_role))
