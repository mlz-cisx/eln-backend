import json

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

FAKE_USER_ID = 1
