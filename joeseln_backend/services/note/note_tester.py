import requests
from joeseln_backend.conf.content_types import *
from joeseln_backend.services.note.note_test_content import CONTENT
from joeseln_backend.conf.base_conf import STATIC_ADMIN_TOKEN

ELN_URL = 'http://localhost:8010/'


class BackendConnector:

    def __init__(self):
        self.eln_url = ELN_URL
        self.headers = {'accept': 'application/json',
                        'Authorization': f'Bearer {STATIC_ADMIN_TOKEN}'}

    def get_notes(self):
        r = requests.get(url=f'{self.eln_url}notes/',
                         headers=self.headers)
        return r.json()

    def create_note(self):
        data = {
            'subject': 'New Note',
            'content': 'New Content'
        }

        r = requests.post(url=f'{self.eln_url}notes/',
                          headers=self.headers, json=data)
        return r.json()

    def create_note_and_add_to_labbook(self, labbook_pk, position_y):
        note_data = {
            'subject': 'Test Note',
            'content': CONTENT
        }

        r = requests.post(url=f'{self.eln_url}notes/',
                          headers=self.headers, json=note_data)

        lb_data = {
            'position_x': 0,
            'position_y': position_y,
            'width': 15,
            'height': 15,
            'child_object_id': r.json()['pk'],
            'child_object_content_type': note_content_type,
            'child_object_content_type_model': note_content_type_model
        }

        r = requests.post(url=f'{self.eln_url}labbooks/{labbook_pk}/elements/',
                          headers=self.headers, json=lb_data)
        return r.json()


# backend_connector = BackendConnector()
# for i in range(1):
#     pos = 15 * i
#     print(backend_connector.create_note_and_add_to_labbook(
#         labbook_pk='f9d3e5df-f75d-47c0-968a-78b035b04715', position_y=pos))
