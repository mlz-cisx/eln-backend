import json
from joeseln_backend.auth.security import get_password_hash

MockUser = json.dumps({
    'available_storage_megabyte': 100,
    'used_storage_megabyte': 50,
    'email': 'alias@domain.com',
    'is_active': True,
    'is_staff': True,
    'permissions': [],
    'pk': 1,
    'username': 'mock_user',
    'userprofile': {
        'academic_title': '',
        'additional_information': '',
        'anonymized': False,
        'country': 'Germany',
        'first_name': 'User',
        'last_name': 'Name',
        'org_zug_mitarbeiter_lang': ['Affiliation 1', 'Affiliation 2',
                                     'Affiliation 3'],
        'org_zug_student_lang': ['Affiliation 1', 'Affiliation 2',
                                 'Affiliation 3'],
        'phone': '',
        'website': '',
        'ui_settings': {},
    }
})

MOCK_USER = {
    'username': 'mock_user',
    'email': 'mock_user@foo.com',
}

TEST_USER_1 = {
    'username': 'admin',
    'email': 'admin@foo.com',
    'oidc_user': False,
    'password': get_password_hash('secret'),
    'first_name': 'admin',
    'last_name': 'admin'
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

FAKE_USER_ID = 1
