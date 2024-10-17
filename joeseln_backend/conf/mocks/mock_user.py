from joeseln_backend.auth.security import get_password_hash

USER0 = {
    'username': 'admin',
    'email': 'admin@foo.com',
    'oidc_user': False,
    'password': get_password_hash('secret'),
    'first_name': 'admin',
    'last_name': 'admin'
}

TEST_USER_1 = {
    'username': 'admin_alt',
    'email': 'admin_alt@foo.com',
    'oidc_user': False,
    'password': get_password_hash('secret'),
    'first_name': 'admin_alt',
    'last_name': 'admin_alt'
}

TEST_USER_2 = {
    'username': 'user1',
    'email': 'user1@foo.com',
    'oidc_user': False,
    'password': get_password_hash('secret'),
    'first_name': 'user1',
    'last_name': 'user1'
}

TEST_USER_3 = {
    'username': 'user2',
    'email': 'user2@foo.com',
    'oidc_user': False,
    'password': get_password_hash('secret'),
    'first_name': 'user2',
    'last_name': 'user2'
}
