import requests
from requests_toolbelt.multipart.encoder import MultipartEncoder

from joeseln_backend.conf.content_types import *

ELN_URL = 'http://localhost:8010/'
TEST_IMG_1 = '/home/jbaudisch/Bilder/original.png'
TEST_IMG_2 = '/home/jbaudisch/Bilder/Logo.png'


class BackendConnector:

    def __init__(self):
        self.eln_url = ELN_URL
        self.headers = {'accept': 'application/json'}

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
        r = requests.post(url=f'{self.eln_url}pictures/',
                          headers={'Content-Type': files.content_type}, data=files)
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
# for i in range(500):
#     pos = 8 * i
#     print(backend_connector.create_image_and_add_to_labbook(
#         labbook_pk='629fa7e1-7ad5-47d7-8098-8949611736f4', position_y=pos))
