LABBOOK_USER = {
    'fullAccess': False,
    'view': True,
    'edit': True,
    'delete': False,
    'trash': False,
    # restore right includes versioning
    'restore': False,
}

ADMIN_NOTES_USER = {
    'fullAccess': False,
    'view': True,
    'edit': False,
    'delete': False,
    'trash': False,
    'restore': False,
}

USER_NOTES_USER = {
    'fullAccess': True,
    'view': True,
    'edit': True,
    'delete': True,
    'trash': True,
    'restore': True,
}

ADMIN_FILES_USER = {
    'fullAccess': False,
    'view': True,
    'edit': False,
    'delete': False,
    'trash': False,
    'restore': False,
}

USER_FILES_USER = {
    'fullAccess': True,
    'view': True,
    'edit': True,
    'delete': True,
    'trash': True,
    'restore': True,
}

ADMIN_PICS_USER = {
    'fullAccess': False,
    'view': True,
    # exception here on pics edit, to add some shapes on background image
    'edit': True,
    'delete': False,
    'trash': False,
    'restore': False,
}

USER_PICS_USER = {
    'fullAccess': True,
    'view': True,
    'edit': True,
    'delete': True,
    'trash': True,
    'restore': True,
}
