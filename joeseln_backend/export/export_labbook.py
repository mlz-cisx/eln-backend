import asyncio
import base64
import json
import os
import tempfile
import zipfile
from io import BytesIO

from fastapi import BackgroundTasks
from fastapi.responses import StreamingResponse
from jinja2 import Environment, FileSystemLoader
from playwright.async_api import async_playwright
from pypdf import PdfWriter, PdfReader
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


async def get_export_data(db, lb_pk, jwt, export_filter: ExportFilter,
                          background_tasks: BackgroundTasks):
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
    # --- chunking ---
    CHUNK_SIZE = 20
    chunks = [elems[i:i + CHUNK_SIZE] for i in range(0, len(elems), CHUNK_SIZE)]

    async with async_playwright() as p:
        browser = await p.chromium.connect(PLAYWRIGHT_WS)

        pdf_parts = []

        for chunk in chunks:
            page = await browser.new_page()

            data = {'instance': lb, 'labbook_child_elements': chunk}
            html = template.render(data)

            await page.set_content(html)

            # inject canvas content for this chunk only
            await asyncio.gather(
                *[
                    page.evaluate(
                        f"""
                    (canvas_json) => {{
                        return new Promise(resolve => {{
                            window.fabricCanvas = new fabric.Canvas('{elem.child_object.id}', {{
                                width: 1000,
                                height: 750,
                                backgroundColor: '#F4F4F4'
                            }});

                            const canvas = JSON.parse(canvas_json);
                            window.fabricCanvas.loadFromJSON(canvas, () => {{
                                const canvasWidth = window.fabricCanvas.getWidth();
                                const canvasHeight = window.fabricCanvas.getHeight();

                                const scaleX = 1000 / canvasWidth;
                                const scaleY = 750 / canvasHeight;
                                const scale = Math.min(scaleX, scaleY);

                                window.fabricCanvas.getObjects().forEach(obj => {{
                                    obj.scaleX *= scale;
                                    obj.scaleY *= scale;
                                    obj.left *= scale;
                                    obj.top *= scale;
                                    obj.setCoords();
                                }});
                                window.fabricCanvas.requestRenderAll();
                                resolve();
                            }});
                        }});
                    }}""",
                        elem.child_object.canvas_content,
                    )
                    for elem in chunk
                    if elem.child_object_content_type == 40
                ]
            )

            await wait_for_mathjax(page)

            pdf_bytes = await page.pdf(format="A4")
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            tmp.write(pdf_bytes)
            tmp.flush()
            tmp.close()
            pdf_parts.append(tmp.name)

            await page.close()

        await browser.close()

    # merge PDFs into a tempfile
    merged_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    merged_tmp.close()
    writer = PdfWriter()

    for path in pdf_parts:
        reader = PdfReader(path)
        for page in reader.pages:
            writer.add_page(page)

    with open(merged_tmp.name, "wb") as f:
        writer.write(f)

    # schedule cleanup of all tempfiles
    for path in pdf_parts:
        background_tasks.add_task(remove_file, path)
    background_tasks.add_task(remove_file, merged_tmp.name)

    # stream the merged PDF
    def iterfile():
        with open(merged_tmp.name, "rb") as f:
            while chunk := f.read(1024 * 1024 * 4):
                yield chunk

    return StreamingResponse(
        iterfile(),
        media_type="application/pdf",
        headers={"Content-Disposition": "inline; filename=labbook_export.pdf"}
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


def remove_file(path: str):
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
