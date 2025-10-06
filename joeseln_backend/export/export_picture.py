import base64
import os
import subprocess

from fastapi.responses import Response
from jinja2 import Environment, FileSystemLoader

from joeseln_backend.auth.security import get_user_from_jwt
from joeseln_backend.services.picture.picture_service import (
    get_picture_for_export,
    get_picture_relations,
)


def get_base64_image(image_path):
    with open(image_path, "rb") as img_file:
        encoded = base64.b64encode(img_file.read()).decode("utf-8")
    return encoded


def get_export_data(db, picture_pk, jwt):
    parent_dir = os.path.dirname(os.path.abspath(__file__))
    render_mathjax_path = os.path.join(parent_dir, "render_mathjax.js")

    user = get_user_from_jwt(db=db, token=jwt)
    if user is None:
        return
    root = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(root, '', 'templates')
    env = Environment(loader=FileSystemLoader(templates_dir))
    template = env.get_template('picture.jinja2')

    db_picture = get_picture_for_export(db=db, picture_pk=picture_pk)
    db_picture_relations = get_picture_relations(db=db, picture_pk=picture_pk,
                                                 params=None, user=user)

    base64_image = get_base64_image(db_picture.rendered_image)

    db_picture.rendered_image = base64_image

    data = {'instance': db_picture, 'picture_relations': db_picture_relations}
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
