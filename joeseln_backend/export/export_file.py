from jinja2 import Environment, FileSystemLoader
import os
from weasyprint import HTML
import io
from fastapi.responses import Response

from joeseln_backend.auth.security import get_user_from_jwt
from joeseln_backend.services.file.file_service import get_file, \
    get_file_relations


def get_export_data(db, file_pk, jwt):
    user = get_user_from_jwt(token=jwt)
    if user is None:
        return
    root = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(root, '', 'templates')
    env = Environment(loader=FileSystemLoader(templates_dir))
    template = env.get_template('file.jinja2')

    db_file = get_file(db=db, file_pk=file_pk, user=user)
    db_file_relations = get_file_relations(db=db, file_pk=file_pk,
                                           params=None)
    # print(vars(db_picture))
    # for elem in elems:
    #     print(vars(elem))
    data = {'instance': db_file, 'file_relations': db_file_relations}
    buf = io.StringIO()
    buf.write(template.render(data))
    buf.seek(0)
    export = HTML(buf).write_pdf()
    return Response(export)
