from jinja2 import Environment, FileSystemLoader
import os
from weasyprint import HTML

root = os.path.dirname(os.path.abspath(__file__))
print(root)
templates_dir = os.path.join(root, '', 'templates')
env = Environment(loader=FileSystemLoader(templates_dir))
template = env.get_template('labbook.jinja2')

from services.labbookchildelements.labbookchildelement_service import get_lb_childelements
from services.labbook.labbook_service import get_labbook
from joeseln_backend.database.database import SessionLocal

db = SessionLocal()
LABBOOK_PK = '6b75e7c7-3608-4742-9e46-2f379792c154'

lb = get_labbook(db=db, labbook_pk=LABBOOK_PK)
print(vars(lb))

elems = get_lb_childelements(db=db, labbook_pk=LABBOOK_PK, as_export=True)
for elem in elems:
    print(vars(elem))

    # if elem.child_object_content_type == 30:
    #     print('Note: ', vars(elem.child_object))
    # if elem.child_object_content_type == 40:
    #     print('Picture: ', vars(elem.child_object))
    # if elem.child_object_content_type == 50:
    #     print('File: ', vars(elem.child_object))

data = {'instance': lb, 'labbook_child_elements': elems}

filename = os.path.join(root, 'html', 'index.html')
with open(filename, 'w') as fh:
    fh.write(template.render(data))
    HTML(filename).write_pdf(os.path.join(root, 'pdf', 'index.pdf'))

# print(template)
