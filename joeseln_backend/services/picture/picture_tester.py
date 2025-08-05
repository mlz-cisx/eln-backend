import requests
from requests_toolbelt.multipart.encoder import MultipartEncoder

from joeseln_backend.conf.base_conf import STATIC_ADMIN_TOKEN
from joeseln_backend.conf.content_types import (
    picture_content_type,
    picture_content_type_model,
)

ELN_URL = 'http://localhost:8010/'
TEST_IMG_1 = '/home/jbaudisch/Bilder/original.png'
TEST_IMG_2 = '/home/jbaudisch/Bilder/Logo.png'


class BackendConnector:

    def __init__(self):
        self.eln_url = ELN_URL
        self.headers = {'accept': 'application/json',
                        'Authorization': f'Bearer {STATIC_ADMIN_TOKEN}'}

    def upload_image(self):
        file = {'file': open(TEST_IMG_1, 'rb')}
        r = requests.post(url=f'{self.eln_url}pictures/',
                          headers=self.headers, files=file)
        return r.json()

    def create_image_and_add_to_labbook(self, labbook_pk, position_y):
        files = MultipartEncoder(
            fields={
                'background_image':
                    ('Logo.png', open(TEST_IMG_2, 'rb')),
                'title': 'test_img',
                'width': '101',
                'height': '61'
            }
        )
        pic_headers = self.headers | {'Content-Type': files.content_type}
        r = requests.post(url=f'{self.eln_url}pictures/',
                          headers=pic_headers, data=files)
        print(r.json())

        lb_data = {
            'position_x': 0,
            'position_y': position_y,
            'width': 15,
            'height': 8,
            'child_object_id': r.json()['pk'],
            'child_object_content_type': picture_content_type,
            'child_object_content_type_model': picture_content_type_model
        }

        r = requests.post(url=f'{self.eln_url}labbooks/{labbook_pk}/elements/',
                          headers=self.headers, json=lb_data)
        print(r)
        return r.json()

# backend_connector = BackendConnector()
# for i in range(200):
#     pos = 8 * i
#     print(backend_connector.create_image_and_add_to_labbook(
#         labbook_pk='8aead5d9-7b76-4832-98e2-d4da41320b4c', position_y=pos))
