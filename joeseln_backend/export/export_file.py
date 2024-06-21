from jinja2 import Environment, FileSystemLoader
import os
from weasyprint import HTML
import io
from fastapi.responses import Response

from joeseln_backend.services.file.file_service import get_file


def get_export_data(db, file_pk, jwt):
    # print(jwt)
    root = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(root, '', 'templates')
    env = Environment(loader=FileSystemLoader(templates_dir))
    template = env.get_template('file.jinja2')

    db_file = get_file(db=db, file_pk=file_pk)
    # print(vars(db_picture))
    # for elem in elems:
    #     print(vars(elem))
    data = {'instance': db_file}
    buf = io.StringIO()
    buf.write(template.render(data))
    buf.seek(0)
    export = HTML(buf).write_pdf()
    return Response(export)