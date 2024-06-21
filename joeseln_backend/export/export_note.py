from jinja2 import Environment, FileSystemLoader
import os
from weasyprint import HTML
import io
from fastapi.responses import Response

from joeseln_backend.services.note.note_service import get_note


def get_export_data(db, note_pk, jwt):
    # print(jwt)
    root = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(root, '', 'templates')
    env = Environment(loader=FileSystemLoader(templates_dir))
    template = env.get_template('note.jinja2')

    db_note = get_note(db=db, note_pk=note_pk)
    # print(vars(lb))
    # for elem in elems:
    #     print(vars(elem))
    data = {'instance': db_note}
    buf = io.StringIO()
    buf.write(template.render(data))
    buf.seek(0)
    export = HTML(buf).write_pdf()
    return Response(export)
