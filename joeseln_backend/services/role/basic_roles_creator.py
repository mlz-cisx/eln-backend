from joeseln_backend.conf.mocks.mock_role import ROLE_USER, ROLE_ADMIN, \
    ROLE_GROUPADMIN
from joeseln_backend.services.role.role_service import create_role, \
    get_role_by_rolename
from joeseln_backend.services.role.role_schema import Role_Create, Role

from joeseln_backend.database.database import SessionLocal

my_session = SessionLocal()


def create_basic_roles():
    if not get_role_by_rolename(db=my_session, rolename='groupadmin'):
        create_role(db=my_session,
                    role=Role_Create.parse_obj(ROLE_GROUPADMIN))
    if not get_role_by_rolename(db=my_session, rolename='user'):
        create_role(db=my_session,
                    role=Role_Create.parse_obj(ROLE_USER))
