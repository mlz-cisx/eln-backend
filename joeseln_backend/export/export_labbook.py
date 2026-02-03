import base64
import json
import os
import zipfile
from io import BytesIO
from typing import List

from fastapi.responses import Response, StreamingResponse
from jinja2 import Environment, FileSystemLoader
from playwright.async_api import async_playwright
from sqlalchemy.orm import Session

from joeseln_backend.auth.security import get_user_from_jwt
from joeseln_backend.conf.base_conf import PLAYWRIGHT_WS
from joeseln_backend.services.labbook.labbook_schemas import ExportFilter
from joeseln_backend.services.labbook.labbook_service import (
    check_for_labbook_access,
    get_labbook_for_export,
)
from joeseln_backend.services.labbookchildelements.labbookchildelement_service import (
    get_lb_childelements_for_export,
    get_lb_childelements_for_zip_export,
)


async def wait_for_mathjax(page):
    # 1. Wait until MathJax is loaded
    await page.wait_for_function("window.MathJax !== undefined")

    # 2. Wait until MathJax startup is ready
    await page.wait_for_function("MathJax.startup && MathJax.startup.promise")

    # 3. Wait for MathJax startup to finish
    await page.evaluate("MathJax.startup.promise")

    # 4. Force a full typeset pass
    await page.evaluate("MathJax.typesetPromise()")

    # 5. Wait until rendered math appears in DOM
    await page.wait_for_function(
        "() => document.querySelector('.mjx-chtml, .MathJax') !== null || !document.body.innerText.match(/[$][^$]+[$]/)"
    )


def get_base64_image(image_path):
    with open(image_path, "rb") as img_file:
        encoded = base64.b64encode(img_file.read()).decode("utf-8")
    return encoded


async def render_fabric_with_puppeteer(page, canvas_data) -> List[str]:
    """
    batch canvas render
    :param page: pyppeteer page
    :param canvas_data: list of canvas content (raw no parse)
    :return image_buffers: list of image in base64
    """
    canvasHeight = 750
    canvasWidth = 1000
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <script src="https://cdnjs.cloudflare.com/ajax/libs/fabric.js/5.3.0/fabric.min.js"></script>
    </head>
    <body>
    <canvas id="c"></canvas>
    <script>
        window.fabricCanvas = new fabric.Canvas('c', {{
          width: {canvasWidth},
          height:  {canvasHeight},
          backgroundColor: '#F4F4F4'
        }});
        window.reorderAlwaysOnTop = function() {{
          const objs = window.fabricCanvas.getObjects();
          objs.forEach(obj => {{
            if (obj.alwaysOnTop) {{
              const idx = window.fabricCanvas._objects.indexOf(obj);
              if (idx > -1) {{
                window.fabricCanvas._objects.splice(idx, 1);
                window.fabricCanvas._objects.push(obj);
              }}
            }}
          }});
          window.fabricCanvas.renderAll();
        }};

        // Hook: whenever a new object is added, re‑push flagged one
        window.fabricCanvas.on('object:added', () => {{
          window.reorderAlwaysOnTop();
        }});

        window.exportAsImage = function() {{
          const exportWidth = {canvasWidth};
          const exportHeight = {canvasHeight};

          const canvasWidth = window.fabricCanvas.getWidth();
          const canvasHeight = window.fabricCanvas.getHeight();

          const scaleX = exportWidth / canvasWidth;
          const scaleY = exportHeight / canvasHeight;
          const scale = Math.min(scaleX, scaleY);

          window.fabricCanvas.getObjects().forEach(obj => {{
            obj.scaleX *= scale;
            obj.scaleY *= scale;
            obj.left *= scale;
            obj.top *= scale;
            obj.setCoords();
          }});

          window.fabricCanvas.renderAll();

          const dataUrl = window.fabricCanvas.toDataURL({{
            format: 'png',
            quality: 1,
            width: exportWidth,
            height: exportHeight,
            multiplier: 1
          }});

          // restore
          window.fabricCanvas.getObjects().forEach(obj => {{
            obj.scaleX /= scale;
            obj.scaleY /= scale;
            obj.left /= scale;
            obj.top /= scale;
            obj.setCoords();
          }});
          window.fabricCanvas.setWidth(canvasWidth);
          window.fabricCanvas.setHeight(canvasHeight);
          window.fabricCanvas.renderAll();
          return dataUrl;
        }};
    </script>
    </body>
    </html>
    """
    await page.set_content(html_content)
    await page.wait_for_selector("#c")  # wail until fabricCanvas is up

    img_buffers = []
    for canvas_json in canvas_data:
        await page.evaluate(
            """(canvas_json) => {{
            return new Promise(resolve => {{
                const canvas = JSON.parse(canvas_json);
                window.fabricCanvas.loadFromJSON(canvas, () => {{
                    window.fabricCanvas.requestRenderAll();
                    resolve();
                }});
            }});
        }}""",
            canvas_json,
        )

        data_url = await page.evaluate("() => window.exportAsImage()")
        base64_data = data_url.replace("data:image/png;base64,", "")
        img_buffers.append(base64_data)

    return img_buffers


async def get_export_data(db, lb_pk, jwt, export_filter: ExportFilter):
    user = get_user_from_jwt(db=db, token=jwt)
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

    contain_types = export_filter.containTypes or []

    # Remove 70 for filtering logic
    types = [t for t in contain_types if t != 70]

    # Apply filtering if any non-70 types remain
    if types:
        elems = [elem for elem in elems if
                 elem.child_object_content_type in types]

    # Clear relations only if user did NOT select comments
    if 70 not in contain_types:
        for elem in elems:
            elem.relations.clear()

    # filter by  user
    if export_filter.users:
        elems = [elem for elem in elems if
                 elem.created_by in export_filter.users]
    # filter by startTime endTime
    if export_filter.startTime and export_filter.startTime.tzinfo is not None:
        filter_start = export_filter.startTime.replace(tzinfo=None)
    else:
        filter_start = export_filter.startTime

    if export_filter.endTime and export_filter.endTime.tzinfo is not None:
        filter_end = export_filter.endTime.replace(tzinfo=None)
    else:
        filter_end = export_filter.endTime

    if filter_start:
        elems = [
            elem
            for elem in elems
            if elem.child_object.created_at > filter_start
        ]

    if filter_end:
        elems = [
            elem
            for elem in elems
            if elem.child_object.created_at < filter_end
        ]

    async with async_playwright() as p:
        # launch browser
        browser = await p.chromium.connect(PLAYWRIGHT_WS)
        page = await browser.new_page()

        # render fabric canvas into base64 image
        farbic_to_render = [
            (elem, elem.child_object.canvas_content)
            for elem in elems
            if elem.child_object_content_type == 40
        ]
        image_buffers = await render_fabric_with_puppeteer(
            page, [canvas for _, canvas in farbic_to_render]
        )
        for (elem, _), img in zip(farbic_to_render, image_buffers):
            elem.child_object.rendered_image = img

        # apply export template
        data = {'instance': lb, 'labbook_child_elements': elems}
        html = template.render(data)

        # render final pdf with mathjax support
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

        await wait_for_mathjax(page)
        pdf_buffer = await page.pdf(format="A4")
        await browser.close()

    return Response(
        content=pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline; filename=mathjax_output.pdf"}
    )


def create_export_zip_file(db: Session, labbook_pk, user,
                           export_filter: ExportFilter):
    if not check_for_labbook_access(db=db, labbook_pk=labbook_pk, user=user):
        return None

    lb = get_labbook_for_export(db=db, labbook_pk=labbook_pk)

    elems = get_lb_childelements_for_zip_export(db=db, labbook_pk=labbook_pk,
                                                user=user,
                                                as_export=True)

    contain_types = export_filter.containTypes or []
    # Remove 70 for filtering logic
    types = [t for t in contain_types if t != 70]
    # Apply filtering if any non-70 types remain
    if types:
        elems = [elem for elem in elems if
                 elem.child_object_content_type in types]

    # Clear relations only if user did NOT select comments
    if 70 not in contain_types:
        for elem in elems:
            elem.relations.clear()
    # filter by  user
    if export_filter.users:
        elems = [elem for elem in elems if
                 elem.created_by in export_filter.users]
    # filter by startTime endTime
    if export_filter.startTime and export_filter.startTime.tzinfo is not None:
        filter_start = export_filter.startTime.replace(tzinfo=None)
    else:
        filter_start = export_filter.startTime
    if export_filter.endTime and export_filter.endTime.tzinfo is not None:
        filter_end = export_filter.endTime.replace(tzinfo=None)
    else:
        filter_end = export_filter.endTime
    if filter_start:
        elems = [
            elem
            for elem in elems
            if elem.child_object.created_at > filter_start
        ]
    if filter_end:
        elems = [
            elem
            for elem in elems
            if elem.child_object.created_at < filter_end
        ]

    elems = [ob.__dict__ for ob in elems]

    for elem in elems:
        elem['child_object'] = elem['child_object'].__dict__
        elem['relations'] = [ob.__dict__ for ob in elem['relations']]

        del elem['_sa_instance_state']

        elem['child_object_id'] = str(elem['child_object_id'])

        del elem['id']
        del elem['labbook_id']

        del elem['child_object']['_sa_instance_state']
        del elem['child_object']['created_at']

        if 'created_by' in elem['child_object']:
            del elem['child_object']['created_by']
        if 'last_modified_by' in elem['child_object']:
            del elem['child_object']['last_modified_by']

        del elem['child_object']['elem_id']
        del elem['child_object']['id']
        del elem['child_object']['last_modified_at']

        if 'uploaded_file_entry_id' in elem['child_object']:
            del elem['child_object']['uploaded_file_entry_id']
        if 'uploaded_picture_entry_id' in elem['child_object']:
            del elem['child_object']['uploaded_picture_entry_id']

        elem['comments'] = []
        for relation in elem['relations']:
            elem['comments'].append(
                (relation['left_content_object'].__dict__)['content'])
        del elem['relations']

    zip_buffer = BytesIO()
    with zipfile.ZipFile(
            file=zip_buffer,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
    ) as zip_archive:
        zip_archive.writestr(zinfo_or_arcname='pictures/', data='')
        zip_archive.writestr(zinfo_or_arcname='files/', data='')

        for elem in elems:
            if elem[
                'child_object_content_type_model'] == 'shared_elements.file':
                dirname = elem['child_object_id']
                filename = elem['child_object']['original_filename']
                try:
                    zip_archive.write(
                        filename=elem['child_object']['path'],
                        arcname=f'files/{dirname}/{filename}')
                except FileNotFoundError:
                    del elem
                else:
                    del elem['child_object']['path']
                    info = {'title': elem['child_object']['title'],
                            'name': elem['child_object']['name'],
                            'file_size': elem['child_object']['file_size'],
                            'description': elem['child_object']['description'],
                            'mime_type': elem['child_object']['mime_type']}

                    zip_archive.writestr(
                        zinfo_or_arcname=f'files/{dirname}/info.json',
                        data=json.dumps(info))


            elif elem['child_object_content_type_model'] == 'pictures.picture':
                dirname = elem['child_object_id']
                try:
                    zip_archive.write(
                        filename=elem['child_object']['background_image'],
                        arcname=f'pictures/{dirname}/bi.png')
                except FileNotFoundError:
                    del elem
                else:
                    del elem['child_object']['background_image']
                    info = {'title': elem['child_object']['title'],
                            'display': elem['child_object']['display'],
                            'canvas_content': elem['child_object'][
                                'canvas_content']}

                    del elem['child_object']['canvas_content']

                    zip_archive.writestr(
                        zinfo_or_arcname=f'pictures/{dirname}/info.json',
                        data=json.dumps(info))

        zip_archive.writestr(zinfo_or_arcname=f'{lb.title}.json',
                             data=json.dumps(elems))

    zip_buffer.seek(0)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename={user.username}.zip"},
    )
