import sys

import requests
from requests_toolbelt.multipart.encoder import MultipartEncoder

from joeseln_backend.conf.base_conf import STATIC_ADMIN_TOKEN
from joeseln_backend.conf.content_types import (
    file_content_type,
    file_content_type_model,
)
from joeseln_backend.services.note.note_test_content import CONTENT

ELN_URL = 'http://localhost:8010/api/'
TEST_IMG_1 = '/home/jbaudisch/Bilder/original.png'
TEST_IMG_2 = '/home/jbaudisch/Bilder/Logo.png'
TEST_IMG_3 = '/home/jbaudisch/Bilder/Text.pdf'

import base64
import io
from pdf2image import convert_from_path

def pdf_page_to_base64_image(pdf_path, dpi=200):
    # Convert first page of PDF to PIL image
    pages = convert_from_path(pdf_path, dpi=dpi)
    img = pages[0]  # single-page PDF

    # Convert image to bytes
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    img_bytes = buffer.getvalue()

    # Encode to base64
    return base64.b64encode(img_bytes).decode("utf-8"), img.size


def build_html_with_image(base64_str, img_size, fixed_width_px=600, element_id="pdf_image"):
    orig_w, orig_h = img_size
    ratio = orig_h / orig_w
    scaled_height = int(fixed_width_px * ratio)

    html = f"""
    <img
        id="{element_id}"
        src="data:image/png;base64,{base64_str}"
        width="{fixed_width_px}"
        height="{scaled_height}"
        style="object-fit: contain;"
    />
    """
    return html


pdf_path = TEST_IMG_3
b64, size = pdf_page_to_base64_image(pdf_path)
html_snippet = build_html_with_image(b64, size)

content = build_html_with_image(b64, size)



class BackendConnector:

    def __init__(self):
        self.eln_url = ELN_URL
        self.headers = {'accept': 'application/json',
                        'Authorization': f'Bearer {STATIC_ADMIN_TOKEN}'}


    def create_file_and_add_to_labbook(self, labbook_pk, position_y):
        my_file= open(TEST_IMG_3, 'rb')
        size = sys.getsizeof(my_file)
        files = MultipartEncoder(
            fields={
                'path':
                    ('Logo.png', my_file),
                'title': 'test_img',
                'name' : 'Text.pdf',
                'file_size': str(size),
                'description': content
            }
        )

        pic_headers = self.headers | {'Content-Type': files.content_type}
        r = requests.post(url=f'{self.eln_url}files/',
                          headers=pic_headers, data=files)


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
        return r.json()


# backend_connector = BackendConnector()
# for i in range(1):
#     pos = 16 * i
#     backend_connector.create_file_and_add_to_labbook(labbook_pk='5c4af6ab-4193-4cd4-aec3-acdbb610dc75', position_y=pos)
