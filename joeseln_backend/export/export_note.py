import os

from fastapi.responses import Response
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright

from joeseln_backend.auth.security import get_user_from_jwt
from joeseln_backend.conf.base_conf import PLAYWRIGHT_WS
from joeseln_backend.services.note.note_service import get_note, get_note_relations


def wait_for_mathjax(page):
    # 1. Wait until MathJax is loaded
    page.wait_for_function("window.MathJax !== undefined")

    # 2. Wait until MathJax startup is ready
    page.wait_for_function("MathJax.startup && MathJax.startup.promise")

    # 3. Wait for MathJax startup to finish
    page.evaluate("MathJax.startup.promise")

    # 4. Force a full typeset pass
    page.evaluate("MathJax.typesetPromise()")

    # 5. Wait until rendered math appears in DOM
    page.wait_for_function(
        "() => document.querySelector('.mjx-chtml, .MathJax') !== null || !document.body.innerText.match(/[$][^$]+[$]/)"
    )


def get_export_data(db, note_pk, jwt):
    user = get_user_from_jwt(db=db, token=jwt)
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

    html = template.render(data)

    with sync_playwright() as p:
        # launch browser
        browser = p.chromium.connect(PLAYWRIGHT_WS)
        page = browser.new_page()
        # render final pdf with mathjax support
        page.set_content(html)
        wait_for_mathjax(page)
        pdf_buffer = page.pdf(format="A4")
        browser.close()

    return Response(
        content=pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline; filename=mathjax_output.pdf"}
    )
