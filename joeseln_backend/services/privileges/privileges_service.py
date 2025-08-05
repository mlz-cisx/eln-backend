from joeseln_backend.services.privileges.admin_privileges.privileges_service import (
    ADMIN,
)
from joeseln_backend.services.privileges.groupadmin_privileges.privileges_service import (
    ADMIN_FILES_GROUPADMIN,
    ADMIN_NOTES_GROUPADMIN,
    ADMIN_PICS_GROUPADMIN,
    LABBOOK_GROUPADMIN,
    USER_FILES_GROUPADMIN,
    USER_NOTES_GROUPADMIN,
    USER_PICS_GROUPADMIN,
)
from joeseln_backend.services.privileges.guest_privileges.privileges_service import (
    GUEST,
)
from joeseln_backend.services.privileges.user_privileges.privileges_service import (
    ADMIN_FILES_USER,
    ADMIN_NOTES_USER,
    ADMIN_PICS_USER,
    LABBOOK_USER,
    USER_FILES_USER,
    USER_NOTES_USER,
    USER_PICS_USER,
)

# TODO factorization necessary


def retrieve_lb_privileges(rolename):
    match rolename:
        case 'admin':
            return ADMIN
        case 'groupadmin':
            return LABBOOK_GROUPADMIN
        case 'user':
            return LABBOOK_USER
        case 'guest':
            return GUEST


def retrieve_user_note_privileges(rolename):
    match rolename:
        case 'admin':
            return ADMIN
        case 'groupadmin':
            return USER_NOTES_GROUPADMIN
        case 'user':
            return USER_NOTES_USER
        case 'guest':
            return GUEST


def retrieve_admin_note_privileges(rolename):
    match rolename:
        case 'admin':
            return ADMIN
        case 'groupadmin':
            return ADMIN_NOTES_GROUPADMIN
        case 'user':
            return ADMIN_NOTES_USER
        case 'guest':
            return GUEST


def retrieve_user_pic_privileges(rolename):
    match rolename:
        case 'admin':
            return ADMIN
        case 'groupadmin':
            return USER_PICS_GROUPADMIN
        case 'user':
            return USER_PICS_USER
        case 'guest':
            return GUEST


def retrieve_admin_pic_privileges(rolename):
    match rolename:
        case 'admin':
            return ADMIN
        case 'groupadmin':
            return ADMIN_PICS_GROUPADMIN
        case 'user':
            return ADMIN_PICS_USER
        case 'guest':
            return GUEST


def retrieve_user_file_privileges(rolename):
    match rolename:
        case 'admin':
            return ADMIN
        case 'groupadmin':
            return USER_FILES_GROUPADMIN
        case 'user':
            return USER_FILES_USER
        case 'guest':
            return GUEST


def retrieve_admin_file_privileges(rolename):
    match rolename:
        case 'admin':
            return ADMIN
        case 'groupadmin':
            return ADMIN_FILES_GROUPADMIN
        case 'user':
            return ADMIN_FILES_USER
        case 'guest':
            return GUEST


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


def create_strict_privileges(created_by):
    self_privileges = {
        'fullAccess': False,
        'view': True,
        'edit': True,
        'delete': True,
        'trash': True,
        'restore': True,
    }

    other_privileges = {
        'fullAccess': False,
        'view': True,
        'edit': False,
        'delete': False,
        'trash': False,
        'restore': False,
    }

    match created_by:
        case 'SELF':
            return self_privileges

        case 'ANOTHER':
            return other_privileges


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
