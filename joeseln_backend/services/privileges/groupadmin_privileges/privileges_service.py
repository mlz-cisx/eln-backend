LABBOOK_GROUPADMIN = {
    'fullAccess': False,
    'view': True,
     # edit right includes versioning
    'edit': True,
    'delete': False,
    'trash': False,
    'restore': True,
}

ADMIN_NOTES_GROUPADMIN = {
    'fullAccess': False,
    'view': True,
    'edit': False,
    'delete': True,
    # to trash and restore elements from instrument
    # in case some data from instrument are not needed
    'trash': True,
    'restore': True,
}

USER_NOTES_GROUPADMIN = {
    'fullAccess': True,
    'view': True,
    'edit': True,
    'delete': True,
    'trash': True,
    'restore': True,
}

ADMIN_FILES_GROUPADMIN = {
    'fullAccess': False,
    'view': True,
    'edit': False,
    'delete': True,
    # to trash and restore elements from instrument
    'trash': True,
    'restore': True,
}

USER_FILES_GROUPADMIN = {
    'fullAccess': True,
    'view': True,
    'edit': True,
    'delete': True,
    'trash': True,
    'restore': True,
}

ADMIN_PICS_GROUPADMIN = {
    'fullAccess': False,
    'view': True,
    # exception here on pics edit, to add some shapes on background image
    'edit': True,
    'delete': True,
    # to trash and restore elements from instrument
    'trash': True,
    'restore': True,
}

USER_PICS_GROUPADMIN = {
    'fullAccess': True,
    'view': True,
    'edit': True,
    'delete': True,
    'trash': True,
    'restore': True,
}
