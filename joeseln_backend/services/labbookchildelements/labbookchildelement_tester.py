import requests

ELN_URL = 'http://localhost:8010/'


class BackendConnector:

    def __init__(self):
        self.eln_url = ELN_URL
        self.headers = {'accept': 'application/json'}

    def get_labbook_elements(self, labbook_pk):
        r = requests.get(url=f'{self.eln_url}labbooks/{labbook_pk}/elements',
                         headers=self.headers)
        return r.json()

    def create_labbookelement(self, labbook_pk):
        data = {
            'position_x': 0,
            'position_y': 0,
            'width': 15,
            'height': 8,
            'child_object_id': "3ee15052-7261-4111-84d0-9074c664f4e2",
            'child_object_content_type': 10,
            'child_object_content_type_model': 'some model'
        }

        r = requests.post(url=f'{self.eln_url}labbooks/{labbook_pk}/elements/',
                          headers=self.headers, json=data)
        return r.json()


# backend_connector = BackendConnector()
# elems = backend_connector.get_labbook_elements(labbook_pk='9aba9e32-e02b-4594-8255-ea65af43f0ea')

