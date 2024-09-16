from joeseln_backend.conf.mocks.mock_role import ROLE_USER, ROLE_GROUPADMIN
from joeseln_backend.conf.mocks.mock_user import USER0
from joeseln_backend.services.role.role_service import create_role, \
    get_role_by_rolename
from joeseln_backend.services.role.role_schema import Role_Create
from joeseln_backend.services.user.user_service import get_user_by_uname, \
    create_user
from joeseln_backend.services.user.user_schema import User_Create
from joeseln_backend.database.database import SessionLocal
from joeseln_backend.services.user_to_group.user_to_group_service import \
    add_admin_role

my_session = SessionLocal()


def create_basic_roles():
    if not get_role_by_rolename(db=my_session, rolename='groupadmin'):
        create_role(db=my_session,
                    role=Role_Create.parse_obj(ROLE_GROUPADMIN))
    if not get_role_by_rolename(db=my_session, rolename='user'):
        create_role(db=my_session,
                    role=Role_Create.parse_obj(ROLE_USER))

def create_inital_admin():
    if not get_user_by_uname(db=my_session, username='admin'):
        create_user(db=my_session,
                                user=User_Create.parse_obj(USER0))
        print(add_admin_role(db=my_session, username='admin'))


