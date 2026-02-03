import os

from fastapi.responses import Response
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright

from joeseln_backend.auth.security import get_user_from_jwt
from joeseln_backend.conf.base_conf import PLAYWRIGHT_WS
from joeseln_backend.services.file.file_service import get_file, get_file_relations


def get_export_data(db, file_pk, jwt):
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
    data = {'instance': db_file, 'file_relations': db_file_relations}
    html = template.render(data)

    with sync_playwright() as p:
        # launch browser
        browser = p.chromium.connect(PLAYWRIGHT_WS)
        page = browser.new_page()
        # render final pdf with mathjax support
        page.set_content(html)
        pdf_buffer = page.pdf(format="A4")
        browser.close()

    return Response(
        content=pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline; filename=mathjax_output.pdf"}
    )
