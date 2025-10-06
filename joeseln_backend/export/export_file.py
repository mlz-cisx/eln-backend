import os
import subprocess

from fastapi.responses import Response
from jinja2 import Environment, FileSystemLoader

from joeseln_backend.auth.security import get_user_from_jwt
from joeseln_backend.services.file.file_service import get_file, \
    get_file_relations


def get_export_data(db, file_pk, jwt):
    parent_dir = os.path.dirname(os.path.abspath(__file__))
    render_mathjax_path = os.path.join(parent_dir, "render_mathjax.js")
    user = get_user_from_jwt(db=db, token=jwt)
    if user is None:
        return
    root = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(root, '', 'templates')
    env = Environment(loader=FileSystemLoader(templates_dir))
    template = env.get_template('file.jinja2')

    db_file = get_file(db=db, file_pk=file_pk, user=user)
    db_file_relations = get_file_relations(db=db, file_pk=file_pk,
                                           params=None, user=user)
    # print(vars(db_picture))
    # for elem in elems:
    #     print(vars(elem))
    data = {'instance': db_file, 'file_relations': db_file_relations}

    html = template.render(data)

    result = subprocess.run(
        ["node",
         render_mathjax_path],
        input=html.encode("utf-8"),
        stdout=subprocess.PIPE,
        check=True
    )

    return Response(
        content=result.stdout,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline; filename=mathjax_output.pdf"}
    )
