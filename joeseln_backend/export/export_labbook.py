import asyncio
import base64
import json
import os
import shutil
import tempfile
import uuid
import zipfile
from datetime import timezone
from io import BytesIO

from cachetools import Cache
from fastapi import BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
from jinja2 import Environment, FileSystemLoader
from playwright.async_api import async_playwright
from pypdf import PdfReader, PdfWriter
from sqlalchemy.orm import Session

from joeseln_backend.conf.base_conf import PLAYWRIGHT_WS, PLAYWRIGHT_MEM, \
    PLAYWRIGHT_CPU
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


pending_export = Cache(maxsize=128)


async def get_export_data(
    db,
    lb_pk,
    user,
    export_identifier: str,
    export_filter: ExportFilter,
    background_tasks: BackgroundTasks,
):
    root = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(root, '', 'templates')
    env = Environment(loader=FileSystemLoader(templates_dir))
    template = env.get_template('labbook.jinja2')
    lb = get_labbook_for_export(db=db, labbook_pk=lb_pk)
    elems = get_lb_childelements_for_export(
        db=db, labbook_pk=lb_pk, access_token="", user=user, as_export=True
    )

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

    pending_export[export_identifier] = merged_tmp.name

    # schedule cleanup of all tempfiles
    for path in pdf_parts:
        background_tasks.add_task(remove_file, path)


def stream_export_response(identifier, background_tasks: BackgroundTasks):
    path = pending_export.get(identifier)
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=204)

    pending_export.pop(identifier)
    background_tasks.add_task(remove_file, path)

    def iterfile():
        with open(path, "rb") as f:
            while chunk := f.read(1024 * 1024 * 4):
                yield chunk

    return StreamingResponse(
        iterfile(),
    )


def create_export_zip_file(
    db: Session, labbook_pk, user, export_identifier: str, export_filter: ExportFilter
):
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

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    tmp_path = tmp.name
    tmp.close()

    with zipfile.ZipFile(
            file=tmp_path,
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

    pending_export[export_identifier] = tmp_path


def remove_file(path: str):
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


async def simple_get_lxf_export_data(
        db,
        labbook_pk,
        user,
        export_identifier: str,
        export_filter: ExportFilter,
):
    root = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(root, '', 'templates')
    env = Environment(loader=FileSystemLoader(templates_dir))

    elems = get_lb_childelements_for_export(
        db=db, labbook_pk=labbook_pk, access_token="", user=user, as_export=True
    )

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

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    tmp_path = tmp.name
    tmp.close()

    manifest = {
        "version": "1.0"
    }
    manifest_pages = []

    with zipfile.ZipFile(
            file=tmp_path,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
    ) as zip_archive:

        zip_archive.writestr(zinfo_or_arcname='pages/', data='')

        for elem in elems:

            # note
            if elem.child_object_content_type == 30:
                template = env.get_template('note.jinja2')
                data = {'instance': elem.child_object,
                        'note_relations': elem.relations}
                html = template.render(data)

                async with async_playwright() as p:
                    # launch browser
                    browser = await p.chromium.connect(PLAYWRIGHT_WS)
                    page = await browser.new_page()
                    # render final pdf with mathjax support
                    await page.set_content(html)
                    await wait_for_mathjax(page)
                    pdf_buffer = await page.pdf(format="A4")
                    await browser.close()

                # --- SPLIT MULTI-PAGE PDF INTO SINGLE-PAGE PDFs ---
                reader = PdfReader(BytesIO(pdf_buffer))

                for i, page in enumerate(reader.pages):
                    page_identifier = str(uuid.uuid4())
                    writer = PdfWriter()
                    writer.add_page(page)

                    single_page_pdf = BytesIO()
                    writer.write(single_page_pdf)
                    single_page_pdf.seek(0)

                    zip_archive.writestr(
                        f"pages/{page_identifier}.pdf",
                        single_page_pdf.read()
                    )

                    continued = f" (continued page {i+1})" if i > 0 else ""

                    manifest_pages.append(
                        {
                            'uuid': page_identifier,
                            'title': f'{elem.child_object.subject}{continued}',
                            'created_at': (
                                elem.child_object.created_at).replace(
                                tzinfo=timezone.utc).replace(
                                microsecond=0).isoformat().replace("+00:00",
                                                                   "Z")
                        }
                    )

            # picture
            if elem.child_object_content_type == 40:
                template = env.get_template('picture.jinja2')

                async with async_playwright() as p:
                    # launch browser
                    browser = await p.chromium.connect(PLAYWRIGHT_WS)
                    page = await browser.new_page()

                    # apply export template
                    data = {'instance': elem.child_object,
                            'picture_relations': elem.relations}
                    html = template.render(data)
                    await page.set_content(html)
                    canvas_id = "c"
                    await page.evaluate(
                        f"""
                        (canvas_json) => {{
                            return new Promise(resolve => {{
                                window.fabricCanvas = new fabric.Canvas('{canvas_id}', {{
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

                    pdf_buffer = await page.pdf(format="A4")
                    await browser.close()

                # --- SPLIT MULTI-PAGE PDF INTO SINGLE-PAGE PDFs ---
                reader = PdfReader(BytesIO(pdf_buffer))

                for i, page in enumerate(reader.pages):
                    page_identifier = str(uuid.uuid4())
                    writer = PdfWriter()
                    writer.add_page(page)

                    single_page_pdf = BytesIO()
                    writer.write(single_page_pdf)
                    single_page_pdf.seek(0)

                    zip_archive.writestr(
                        f"pages/{page_identifier}.pdf",
                        single_page_pdf.read()
                    )
                    continued = f" (continued page {i+1})" if i > 0 else ""

                    manifest_pages.append(
                        {
                            'uuid': page_identifier,
                            'title': f'{elem.child_object.title}{continued}',
                            'created_at': (
                                elem.child_object.created_at).replace(
                                tzinfo=timezone.utc).replace(
                                microsecond=0).isoformat().replace("+00:00",
                                                                   "Z")
                        }
                    )

            # file
            if elem.child_object_content_type == 50:
                template = env.get_template('file.jinja2')
                data = {'instance': elem.child_object,
                        'file_relations': elem.relations}
                html = template.render(data)

                async with async_playwright() as p:
                    # launch browser
                    browser = await p.chromium.connect(PLAYWRIGHT_WS)
                    page = await browser.new_page()
                    await page.set_content(html)
                    pdf_buffer = await page.pdf(format="A4")
                    await browser.close()

                # --- SPLIT MULTI-PAGE PDF INTO SINGLE-PAGE PDFs ---
                reader = PdfReader(BytesIO(pdf_buffer))

                for i, page in enumerate(reader.pages):
                    page_identifier = str(uuid.uuid4())
                    writer = PdfWriter()
                    writer.add_page(page)

                    single_page_pdf = BytesIO()
                    writer.write(single_page_pdf)
                    single_page_pdf.seek(0)

                    zip_archive.writestr(
                        f"pages/{page_identifier}.pdf",
                        single_page_pdf.read()
                    )
                    continued = f" (continued page {i+1})" if i > 0 else ""

                    manifest_pages.append(
                        {
                            'uuid': page_identifier,
                            'title': f'{elem.child_object.title}{continued}',
                            'created_at': (
                                elem.child_object.created_at).replace(
                                tzinfo=timezone.utc).replace(
                                microsecond=0).isoformat().replace("+00:00",
                                                                   "Z")
                        }
                    )

        manifest['pages'] = manifest_pages
        zip_archive.writestr(zinfo_or_arcname='manifest.json',
                             data=json.dumps(manifest, indent=2,
                                             ensure_ascii=False))

    pending_export[export_identifier] = tmp_path


async def get_lxf_export_data(
        db,
        labbook_pk,
        user,
        export_identifier: str,
        export_filter: ExportFilter,
):
    # ----------------------------
    # Templates
    # ----------------------------
    root = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(root, '', 'templates')
    env = Environment(loader=FileSystemLoader(templates_dir))
    note_template = env.get_template('note.jinja2')
    picture_template = env.get_template('picture.jinja2')
    file_template = env.get_template('file.jinja2')

    # ----------------------------
    # Load elements
    # ----------------------------
    elems = get_lb_childelements_for_export(
        db=db, labbook_pk=labbook_pk, access_token="", user=user, as_export=True
    )

    contain_types = export_filter.containTypes or []
    types = [t for t in contain_types if t != 70]

    if types:
        elems = [elem for elem in elems if
                 elem.child_object_content_type in types]

    if 70 not in contain_types:
        for elem in elems:
            elem.relations.clear()

    if export_filter.users:
        elems = [elem for elem in elems if
                 elem.created_by in export_filter.users]

    # ----------------------------
    # Time filtering
    # ----------------------------
    if export_filter.startTime and export_filter.startTime.tzinfo is not None:
        filter_start = export_filter.startTime.replace(tzinfo=None)
    else:
        filter_start = export_filter.startTime

    if export_filter.endTime and export_filter.endTime.tzinfo is not None:
        filter_end = export_filter.endTime.replace(tzinfo=None)
    else:
        filter_end = export_filter.endTime

    if filter_start:
        elems = [elem for elem in elems if
                 elem.child_object.created_at > filter_start]

    if filter_end:
        elems = [elem for elem in elems if
                 elem.child_object.created_at < filter_end]

    # ----------------------------
    # ZIP temp file
    # ----------------------------
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    tmp_path = tmp.name
    tmp.close()

    manifest = {"version": "1.0"}

    # ----------------------------
    # Temp directory for pages
    # ----------------------------
    page_tmp_dir = tempfile.mkdtemp(prefix="lxf_pages_")

    # ----------------------------
    # Kubernetes-aware pool sizing
    # ----------------------------
    def compute_k8s_pool_sizes():
        # Chromium ~400–600 MB each
        browsers = max(1, min(3, PLAYWRIGHT_MEM // 500))
        browsers = min(browsers, PLAYWRIGHT_CPU)

        # 1–2 pages per browser, capped
        pages = max(1, min(2 * browsers, 6))

        return browsers, pages

    browsers_count, pages_count = compute_k8s_pool_sizes()

    # ----------------------------
    # Start Playwright once
    # ----------------------------
    playwright = await async_playwright().start()

    browsers = [
        await playwright.chromium.connect(PLAYWRIGHT_WS)
        for _ in range(browsers_count)
    ]

    PAGE_LIMIT = asyncio.Semaphore(pages_count)

    # ----------------------------
    # Render element using a browser
    # ----------------------------
    async def render_element_with_browser(browser, elem):
        async with PAGE_LIMIT:
            page = await browser.new_page()
            ctype = elem.child_object_content_type

            # NOTE
            if ctype == 30:
                html = note_template.render({
                    'instance': elem.child_object,
                    'note_relations': elem.relations
                })
                await page.set_content(html)
                await wait_for_mathjax(page)
                pdf_buffer = await page.pdf(format="A4")
                title_base = elem.child_object.subject

            # PICTURE
            elif ctype == 40:
                html = picture_template.render({
                    'instance': elem.child_object,
                    'picture_relations': elem.relations
                })
                await page.set_content(html)

                canvas_id = "c"
                await page.evaluate(
                    f"""
                    (canvas_json) => {{
                        return new Promise(resolve => {{
                            window.fabricCanvas = new fabric.Canvas('{canvas_id}', {{
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

                pdf_buffer = await page.pdf(format="A4")
                title_base = elem.child_object.title

            # FILE
            elif ctype == 50:
                html = file_template.render({
                    'instance': elem.child_object,
                    'file_relations': elem.relations
                })
                await page.set_content(html)
                pdf_buffer = await page.pdf(format="A4")
                title_base = elem.child_object.title

            else:
                await page.close()
                return []

            await page.close()

        # ----------------------------
        # Split PDF and write pages to temp FS
        # ----------------------------
        reader = PdfReader(BytesIO(pdf_buffer))
        results = []

        for i, p in enumerate(reader.pages):
            page_identifier = str(uuid.uuid4())
            writer = PdfWriter()
            writer.add_page(p)

            pdf_path = os.path.join(page_tmp_dir, f"{page_identifier}.pdf")
            with open(pdf_path, "wb") as f:
                writer.write(f)

            continued = f" (continued page {i + 1})" if i > 0 else ""

            created_at = (
                elem.child_object.created_at
                .replace(tzinfo=timezone.utc)
                .replace(microsecond=0)
                .isoformat()
                .replace("+00:00", "Z")
            )

            results.append({
                "uuid": page_identifier,
                "title": f"{title_base}{continued}",
                "created_at": created_at,
                "pdf_path": pdf_path,
            })

        return results

    # ----------------------------
    # Queue + Workers
    # ----------------------------
    task_queue = asyncio.Queue()
    result_list = []  # flat list of page metadata

    for elem in elems:
        await task_queue.put(elem)

    for _ in browsers:
        await task_queue.put(None)

    async def browser_worker(browser):
        while True:
            elem = await task_queue.get()
            if elem is None:
                task_queue.task_done()
                break

            pages = await render_element_with_browser(browser, elem)
            result_list.extend(pages)

            task_queue.task_done()

    workers = [asyncio.create_task(browser_worker(browser)) for browser in
               browsers]

    await task_queue.join()

    for w in workers:
        await w

    # ----------------------------
    # Close browsers + Playwright
    # ----------------------------
    for b in browsers:
        await b.close()
    await playwright.stop()

    # ----------------------------
    # Write ZIP from temp files
    # ----------------------------
    manifest_pages = []

    try:
        with zipfile.ZipFile(
                file=tmp_path,
                mode="w",
                compression=zipfile.ZIP_DEFLATED,
                compresslevel=9,
        ) as zip_archive:

            zip_archive.writestr("pages/", "")

            for page in result_list:
                with open(page["pdf_path"], "rb") as f:
                    zip_archive.writestr(
                        f"pages/{page['uuid']}.pdf",
                        f.read()
                    )

                manifest_pages.append({
                    "uuid": page["uuid"],
                    "title": page["title"],
                    "created_at": page["created_at"]
                })

            manifest["pages"] = manifest_pages

            zip_archive.writestr(
                "manifest.json",
                json.dumps(manifest, indent=2, ensure_ascii=False,
                           sort_keys=True) + "\n"
            )
    finally:
        # ----------------------------
        # Cleanup temp page directory
        # ----------------------------
        shutil.rmtree(page_tmp_dir, ignore_errors=True)

    pending_export[export_identifier] = tmp_path
