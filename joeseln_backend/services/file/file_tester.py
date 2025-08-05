import sys

import requests
from requests_toolbelt.multipart.encoder import MultipartEncoder

from joeseln_backend.conf.base_conf import STATIC_ADMIN_TOKEN
from joeseln_backend.conf.content_types import (
    file_content_type,
    file_content_type_model,
)

ELN_URL = 'http://localhost:8010/api/'
TEST_IMG_1 = '/home/jbaudisch/Bilder/original.png'
TEST_IMG_2 = '/home/jbaudisch/Bilder/Logo.png'


class BackendConnector:

    def __init__(self):
        self.eln_url = ELN_URL
        self.headers = {'accept': 'application/json',
                        'Authorization': f'Bearer {STATIC_ADMIN_TOKEN}'}


    def create_file_and_add_to_labbook(self, labbook_pk, position_y):
        my_file= open(TEST_IMG_2, 'rb')
        size = sys.getsizeof(my_file)
        files = MultipartEncoder(
            fields={
                'path':
                    ('Logo.png', my_file),
                'title': 'test_img',
                'name' : 'Test_name',
                'file_size': str(size),
                'description': ''
            }
        )

        pic_headers = self.headers | {'Content-Type': files.content_type}
        r = requests.post(url=f'{self.eln_url}files/',
                          headers=pic_headers, data=files)
        print(r.json()['pk'])

        lb_data = {
            'position_x': 0,
            'position_y': position_y,
            'width': 15,
            'height': 8,
            'child_object_id': r.json()['pk'],
            'child_object_content_type': file_content_type,
            'child_object_content_type_model': file_content_type_model
        }

        r = requests.post(url=f'{self.eln_url}labbooks/{labbook_pk}/elements/',
                          headers=self.headers, json=lb_data)
        print(r)
        return r.json()


# backend_connector = BackendConnector()
# for i in range(2):
#     pos = 8 * i
#     print(backend_connector.create_file_and_add_to_labbook(
#         labbook_pk='629fa7e1-7ad5-47d7-8098-8949611736f4', position_y=pos))
