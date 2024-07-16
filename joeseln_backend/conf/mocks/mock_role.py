ROLE_ADMIN = {
    'rolename': 'admin',
    'description': 'admin has full rights on all routes'
}


ROLE_USER = {
    'rolename': 'user',
    'description': 'user has rights on all routes touching labbooks referring to groupname'
                   'Rights in detail: '
                   'create new elements in labbook'
                   'read/edit  access on all elements created by groupmembers'
                   'read access on all elements coming from instrument'
                   'put shapes on images coming from instrument'
}

ROLE_GROUPADMIN = {
    'rolename': 'groupadmin',
    'description': 'user has rights on all routes touching labbooks referring to groupname'
                   'Rights in detail: '
                   'all versioning rights on labbook'
                   'create new elements in labbook'
                   'read/edit/thrash/restore access on all elements created by groupmembers'
                   'read access on all elements coming from instrument'
                   'put shapes on images coming from instrument'
}
