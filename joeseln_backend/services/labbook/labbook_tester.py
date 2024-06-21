import requests

ELN_URL = 'http://localhost:8010/'


class BackendConnector:

    def __init__(self):
        self.eln_url = ELN_URL
        self.headers = {'accept': 'application/json'}

    def get_labbooks(self):
        r = requests.get(url=f'{self.eln_url}labbooks/',
                         headers=self.headers)
        return r.json()

    def create_labbook(self, labbook_title):
        labbook_title = 'new labbook'
        data = {
            'title': labbook_title,
            'description': 'very nice'
        }
        r = requests.post(url=f'{self.eln_url}labbooks/',
                          headers=self.headers, json=data)
        return r.json()

    def get_labbook_export_link(self, labbook_pk):
        r = requests.get(url=f'{self.eln_url}labbooks/{labbook_pk}/get_export_link/',
                          headers=self.headers)
        return r.json()

    def get_labbook_export_data(self, labbook_pk):
        r = requests.get(url=f'{self.eln_url}labbooks/{labbook_pk}/export?jwt=foo',
                          headers=self.headers)
        return r


# backend_connector = BackendConnector()
# print(backend_connector.get_labbook_export_data(labbook_pk='6b75e7c7-3608-4742-9e46-2f379792c154'))
