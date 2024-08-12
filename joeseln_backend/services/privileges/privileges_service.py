from joeseln_backend.services.privileges.admin_privileges.privileges_service import \
    ADMIN
from joeseln_backend.services.privileges.groupadmin_privileges.privileges_service import \
    LABBOOK_GROUPADMIN
from joeseln_backend.services.privileges.user_privileges.privileges_service import \
    LABBOOK_USER


def retrieve_lb_privileges(rolename):
    match rolename:
        case 'admin':
            return ADMIN
        case 'groupadmin':
            return LABBOOK_GROUPADMIN
        case 'user':
            return LABBOOK_USER


def create_labbook_privileges(user_roles):
    privileges = {
        'fullAccess': False,
        'view': False,
        'edit': False,
        'delete': False,
        'trash': False,
        'restore': False,
    }

    for role in user_roles:
        privilege = retrieve_lb_privileges(rolename=role[0])
        for i in privilege:
            if privilege[i]:
                privileges[i] = True

    return privileges
