from jinja2 import Environment, FileSystemLoader
import os
from weasyprint import HTML
import io
from fastapi.responses import Response

from joeseln_backend.services.labbookchildelements.labbookchildelement_service import \
    get_lb_childelements_for_export
from joeseln_backend.services.labbook.labbook_service import \
    get_labbook_for_export
from joeseln_backend.auth.security import get_user_from_jwt


def get_export_data(db, lb_pk, jwt):
    user = get_user_from_jwt(token=jwt)
    if user is None:
        return
    root = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(root, '', 'templates')
    env = Environment(loader=FileSystemLoader(templates_dir))
    template = env.get_template('labbook.jinja2')
    lb = get_labbook_for_export(db=db, labbook_pk=lb_pk)
    elems = get_lb_childelements_for_export(db=db, labbook_pk=lb_pk,
                                            access_token=jwt, user=user,
                                            as_export=True)
    data = {'instance': lb, 'labbook_child_elements': elems}
    buf = io.StringIO()
    buf.write(template.render(data))
    buf.seek(0)
    export = HTML(buf).write_pdf()
    return Response(export)
