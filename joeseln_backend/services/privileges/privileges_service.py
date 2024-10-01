from joeseln_backend.services.privileges.admin_privileges.privileges_service import \
    ADMIN
from joeseln_backend.services.privileges.groupadmin_privileges.privileges_service import \
    LABBOOK_GROUPADMIN, USER_NOTES_GROUPADMIN, ADMIN_NOTES_GROUPADMIN, \
    USER_PICS_GROUPADMIN, ADMIN_PICS_GROUPADMIN, USER_FILES_GROUPADMIN, \
    ADMIN_FILES_GROUPADMIN
from joeseln_backend.services.privileges.user_privileges.privileges_service import \
    LABBOOK_USER, USER_NOTES_USER, ADMIN_NOTES_USER, USER_PICS_USER, \
    ADMIN_PICS_USER, USER_FILES_USER, ADMIN_FILES_USER


# TODO factorization necessary


def retrieve_lb_privileges(rolename):
    match rolename:
        case 'admin':
            return ADMIN
        case 'groupadmin':
            return LABBOOK_GROUPADMIN
        case 'user':
            return LABBOOK_USER


def retrieve_user_note_privileges(rolename):
    match rolename:
        case 'admin':
            return ADMIN
        case 'groupadmin':
            return USER_NOTES_GROUPADMIN
        case 'user':
            return USER_NOTES_USER


def retrieve_admin_note_privileges(rolename):
    match rolename:
        case 'admin':
            return ADMIN
        case 'groupadmin':
            return ADMIN_NOTES_GROUPADMIN
        case 'user':
            return ADMIN_NOTES_USER


def retrieve_user_pic_privileges(rolename):
    match rolename:
        case 'admin':
            return ADMIN
        case 'groupadmin':
            return USER_PICS_GROUPADMIN
        case 'user':
            return USER_PICS_USER


def retrieve_admin_pic_privileges(rolename):
    match rolename:
        case 'admin':
            return ADMIN
        case 'groupadmin':
            return ADMIN_PICS_GROUPADMIN
        case 'user':
            return ADMIN_PICS_USER


def retrieve_user_file_privileges(rolename):
    match rolename:
        case 'admin':
            return ADMIN
        case 'groupadmin':
            return USER_FILES_GROUPADMIN
        case 'user':
            return USER_FILES_USER


def retrieve_admin_file_privileges(rolename):
    match rolename:
        case 'admin':
            return ADMIN
        case 'groupadmin':
            return ADMIN_FILES_GROUPADMIN
        case 'user':
            return ADMIN_FILES_USER


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


def create_note_privileges(created_by, user_roles):
    privileges = {
        'fullAccess': False,
        'view': False,
        'edit': False,
        'delete': False,
        'trash': False,
        'restore': False,
    }

    match created_by:
        case 'ADMIN':
            for role in user_roles:
                privilege = retrieve_admin_note_privileges(rolename=role[0])
                for i in privilege:
                    if privilege[i]:
                        privileges[i] = True

            return privileges

        case 'USER':
            for role in user_roles:
                privilege = retrieve_user_note_privileges(rolename=role[0])
                for i in privilege:
                    if privilege[i]:
                        privileges[i] = True

            return privileges


def create_file_privileges(created_by, user_roles):
    privileges = {
        'fullAccess': False,
        'view': False,
        'edit': False,
        'delete': False,
        'trash': False,
        'restore': False,
    }

    match created_by:
        case 'ADMIN':
            for role in user_roles:
                privilege = retrieve_admin_file_privileges(rolename=role[0])
                for i in privilege:
                    if privilege[i]:
                        privileges[i] = True

            return privileges

        case 'USER':
            for role in user_roles:
                privilege = retrieve_user_file_privileges(rolename=role[0])
                for i in privilege:
                    if privilege[i]:
                        privileges[i] = True

            return privileges


def create_pic_privileges(created_by, user_roles):
    privileges = {
        'fullAccess': False,
        'view': False,
        'edit': False,
        'delete': False,
        'trash': False,
        'restore': False,
    }

    match created_by:
        case 'ADMIN':
            for role in user_roles:
                privilege = retrieve_admin_pic_privileges(rolename=role[0])
                for i in privilege:
                    if privilege[i]:
                        privileges[i] = True

            return privileges

        case 'USER':
            for role in user_roles:
                privilege = retrieve_user_pic_privileges(rolename=role[0])
                for i in privilege:
                    if privilege[i]:
                        privileges[i] = True

            return privileges
