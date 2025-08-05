import io
import os

from fastapi.responses import Response
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from joeseln_backend.auth.security import get_user_from_jwt
from joeseln_backend.services.note.note_service import get_note, get_note_relations


def get_export_data(db, note_pk, jwt):
    user = get_user_from_jwt(token=jwt)
    if user is None:
        return
    root = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(root, '', 'templates')
    env = Environment(loader=FileSystemLoader(templates_dir))
    template = env.get_template('note.jinja2')

    db_note = get_note(db=db, note_pk=note_pk)
    db_note_relations = get_note_relations(db=db, note_pk=note_pk,
                                           params=None,
                                           user=user)
    data = {'instance': db_note, 'note_relations': db_note_relations}
    buf = io.StringIO()
    buf.write(template.render(data))
    buf.seek(0)
    export = HTML(buf).write_pdf()
    return Response(export)
