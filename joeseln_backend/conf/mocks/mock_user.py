from joeseln_backend.auth.security import get_password_hash
from joeseln_backend.conf.base_conf import INTRUMNENT_AS_ADMIN, INITIAL_ADMIN

USER0 = {
    'username': INITIAL_ADMIN,
    'email': f'{INITIAL_ADMIN}@foo.com',
    'oidc_user': False,
    'password': get_password_hash('secret'),
    'first_name': INITIAL_ADMIN,
    'last_name': INITIAL_ADMIN
}

INSTRUMENT = {
    'username': INTRUMNENT_AS_ADMIN,
    'email': f'{INTRUMNENT_AS_ADMIN}@foo.com',
    'oidc_user': False,
    'password': get_password_hash('secret'),
    'first_name': INTRUMNENT_AS_ADMIN,
    'last_name': INTRUMNENT_AS_ADMIN,
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
