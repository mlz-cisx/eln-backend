import io
import json
import os
import zipfile
from io import BytesIO

from fastapi.responses import Response, StreamingResponse
from jinja2 import Environment, FileSystemLoader
from sqlalchemy.orm import Session
from weasyprint import HTML

from joeseln_backend.auth.security import get_user_from_jwt
from joeseln_backend.services.labbook.labbook_service import (
    check_for_labbook_access,
    get_labbook_for_export,
)
from joeseln_backend.services.labbookchildelements.labbookchildelement_service import (
    get_lb_childelements_for_export,
    get_lb_childelements_for_zip_export,
)


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

        del elem['created_at']
        del elem['id']
        del elem['labbook_id']
        del elem['last_modified_at']
        del elem['last_modified_by_id']

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
                    zip_archive.write(
                        filename=elem['child_object']['rendered_image'],
                        arcname=f'pictures/{dirname}/ri.png')
                    zip_archive.write(
                        filename=elem['child_object']['shapes_image'],
                        arcname=f'pictures/{dirname}/shapes.json')
                except FileNotFoundError:
                    del elem
                else:
                    del elem['child_object']['background_image']
                    del elem['child_object']['rendered_image']
                    del elem['child_object']['shapes_image']

                    info = {'title': elem['child_object']['title'],
                            'display': elem['child_object']['display'],
                            'width': elem['child_object']['width'],
                            'height': elem['child_object']['height'],
                            'size': elem['child_object'][
                                'background_image_size']}

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
