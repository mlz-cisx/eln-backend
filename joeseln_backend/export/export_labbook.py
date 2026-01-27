import base64
import json
import os
import subprocess
import zipfile
from io import BytesIO

from fastapi.responses import Response, StreamingResponse
from jinja2 import Environment, FileSystemLoader
from sqlalchemy.orm import Session

from joeseln_backend.auth.security import get_user_from_jwt
from joeseln_backend.services.labbook.labbook_schemas import ExportFilter
from joeseln_backend.services.labbook.labbook_service import (
    check_for_labbook_access,
    get_labbook_for_export,
)
from joeseln_backend.services.labbookchildelements.labbookchildelement_service import (
    get_lb_childelements_for_export,
    get_lb_childelements_for_zip_export,
)


def get_base64_image(image_path):
    with open(image_path, "rb") as img_file:
        encoded = base64.b64encode(img_file.read()).decode("utf-8")
    return encoded


def get_export_data(db, lb_pk, jwt, export_filter: ExportFilter):
    parent_dir = os.path.dirname(os.path.abspath(__file__))
    render_mathjax_path = os.path.join(parent_dir, "render_mathjax.js")
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
        elems = [elem for elem in elems if elem.created_by in export_filter.users]
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

    for elem in elems:
        if elem.child_object_content_type == 40:
            render_fabric_js_path = os.path.join(parent_dir, "render_fabric.js")
            canvas_content = json.loads(elem.child_object.canvas_content)

            fabric_data = {
                "canvasWidth": elem.child_object.canvas_width,
                "canvasHeight": elem.child_object.canvas_height,
                "canvas_content": canvas_content
            }

            img = subprocess.run(
                ["node",
                 render_fabric_js_path],
                input=json.dumps(fabric_data).encode("utf-8"),
                stdout=subprocess.PIPE,
                check=True
            )
            png_bytes = img.stdout
            # Encode to base64 string
            encoded = base64.b64encode(png_bytes).decode("utf-8")
            elem.child_object.rendered_image = encoded

    data = {'instance': lb, 'labbook_child_elements': elems}
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


def create_export_zip_file(db: Session, labbook_pk, user):
    if not check_for_labbook_access(db=db, labbook_pk=labbook_pk, user=user):
        return None

    lb = get_labbook_for_export(db=db, labbook_pk=labbook_pk)

    elems = get_lb_childelements_for_zip_export(db=db, labbook_pk=labbook_pk,
                                                user=user,
                                                as_export=True)

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
                            'canvas_content': elem['child_object']['canvas_content']}

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
