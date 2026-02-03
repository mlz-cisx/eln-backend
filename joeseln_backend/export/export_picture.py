import base64
import os

from fastapi.responses import Response
from jinja2 import Environment, FileSystemLoader
from playwright.async_api import async_playwright

from joeseln_backend.auth.security import get_user_from_jwt
from joeseln_backend.conf.base_conf import PLAYWRIGHT_WS
from joeseln_backend.export.export_labbook import render_fabric_with_puppeteer
from joeseln_backend.services.picture.picture_service import (
    get_picture_for_export,
    get_picture_relations,
)


def get_base64_image(image_path):
    with open(image_path, "rb") as img_file:
        encoded = base64.b64encode(img_file.read()).decode("utf-8")
    return encoded


async def get_export_data(db, picture_pk, jwt):
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

    async with async_playwright() as p:
        # launch browser
        browser = await p.chromium.connect(PLAYWRIGHT_WS)
        page = await browser.new_page()

        image_buffer = await render_fabric_with_puppeteer(page, [
            db_picture.canvas_content])
        db_picture.rendered_image = image_buffer[0]
        # apply export template
        data = {'instance': db_picture,
                'picture_relations': db_picture_relations}
        html = template.render(data)

        # render final pdf
        await page.set_content(html)
        # wait for all images to load
        await page.evaluate(
            """async () => {
            const selectors = Array.from(document.images).map(img => {
                if (img.complete) return null;
                return new Promise(resolve => {
                    img.addEventListener('load', resolve);
                    img.addEventListener('error', resolve); // resolve even if image fails to load
                });
            }).filter(p => p !== null);
            await Promise.all(selectors);
        }"""
        )
        pdf_buffer = await page.pdf(format="A4")
        await browser.close()

    return Response(
        content=pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline; filename=mathjax_output.pdf"}
    )
