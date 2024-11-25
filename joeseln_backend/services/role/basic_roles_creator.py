from joeseln_backend.conf.mocks.mock_role import ROLE_USER, ROLE_GROUPADMIN
from joeseln_backend.conf.mocks.mock_user import USER0, INSTRUMENT, \
    INTRUMNENT_AS_ADMIN, INITIAL_ADMIN
from joeseln_backend.services.role.role_service import create_role, \
    get_role_by_rolename
from joeseln_backend.services.role.role_schema import Role_Create
from joeseln_backend.services.user.user_service import get_user_by_uname, \
    create_admin
from joeseln_backend.services.user.user_schema import UserCreate
from joeseln_backend.database.database import SessionLocal

my_session = SessionLocal()


def create_basic_roles():
    if not get_role_by_rolename(db=my_session, rolename='groupadmin'):
        create_role(db=my_session,
                    role=Role_Create.parse_obj(ROLE_GROUPADMIN))
    if not get_role_by_rolename(db=my_session, rolename='user'):
        create_role(db=my_session,
                    role=Role_Create.parse_obj(ROLE_USER))


def create_inital_admin():
    if not get_user_by_uname(db=my_session, username=INITIAL_ADMIN):
        create_admin(db=my_session,
                     user=UserCreate.parse_obj(USER0))

    if not get_user_by_uname(db=my_session, username=INTRUMNENT_AS_ADMIN):
        create_admin(db=my_session,
                     user=UserCreate.parse_obj(INSTRUMENT))
