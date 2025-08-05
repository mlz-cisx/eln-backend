from joeseln_backend.database.database import SessionLocal
from joeseln_backend.services.role.role_schema import Role
from joeseln_backend.services.role.role_service import get_role_by_rolename

my_session = SessionLocal()

# test_role = create_role(db=my_session, role=Role_Create.parse_obj(ROLE_GROUPADMIN))
test_role = get_role_by_rolename(db=my_session, rolename='groupadmin')
print(Role.parse_obj(test_role))
