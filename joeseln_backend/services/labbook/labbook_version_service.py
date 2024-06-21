from sqlalchemy.orm import Session
import json
from sqlalchemy.exc import SQLAlchemyError

from joeseln_backend.models import models
from joeseln_backend.services.note.note_schemas import *
from joeseln_backend.services.picture import picture_version_service
from joeseln_backend.services.note import note_version_service
from joeseln_backend.services.file import file_version_service
from joeseln_backend.conf.mocks.mock_user import FAKE_USER_ID

from joeseln_backend.mylogging.root_logger import logger




def get_all_labbook_versions(db: Session, labbook_pk):
    db_labbook_versions = db.query(models.Version).filter_by(
        object_id=labbook_pk).order_by(models.Version.number.desc()).all()
    # renaming and json.dumps for schema
    for db_labbook_version in db_labbook_versions:
        db_labbook_version.metadata = json.dumps(
            json.loads(json.dumps(db_labbook_version.version_metadata)))
    return db_labbook_versions


def get_labbook_version_metadata(db: Session, version_pk):
    db_labbook_version = db.query(models.Version).get(version_pk)
    # renaming and json.dumps for schema
    return db_labbook_version.version_metadata


def restore_labbook_version(db: Session, labbook_pk, version_pk):
    db_labbook_version = db.query(models.Version).get(version_pk)
    version_metadata = db_labbook_version.version_metadata

    number = db_labbook_version.number

    summary = f'restored from LabbookVersion v{number} '
    # 1 .restore child elements content, description,...
    for elem in version_metadata['child_elements']:
        if elem['type'] == 'Note':
            version = db.query(models.Version).get(
                elem['child_object_version_id'])
            content = version.version_metadata['content']
            subject = version.version_metadata['subject']
            note_version_service.add_note_version(db=db,
                                                  note_pk=elem[
                                                      'child_object_id'],
                                                  summary=summary,
                                                  restored_content=content,
                                                  restored_subject=subject)

        if elem['type'] == 'Picture':
            version = db.query(models.Version).get(
                elem['child_object_version_id'])
            title = version.version_metadata['title']
            ri_img = version.version_metadata['ri_img']
            shapes = version.version_metadata['shapes']
            picture_version_service.add_picture_version(db=db,
                                                        picture_pk=elem[
                                                            'child_object_id'],
                                                        summary=summary,
                                                        restored_title=title,
                                                        restored_ri_img=ri_img,
                                                        restored_shapes=shapes)
        if elem['type'] == 'File':
            version = db.query(models.Version).get(
                elem['child_object_version_id'])
            title = version.version_metadata['title']
            description = version.version_metadata['description']
            file_version_service.add_file_version(db=db,
                                                  file_pk=elem[
                                                      'child_object_id'],
                                                  summary=summary,
                                                  restored_title=title,
                                                  restored_description=description)

    # 2. restore child elements position
    update_all_lb_childelements_from_version(db=db, labbook_childelems=
    version_metadata['child_elements'])

    summary = f'restored from v{db_labbook_version.number}'
    version_metadata = db_labbook_version.version_metadata
    title = version_metadata['title']
    db_labbook = add_labbook_version(db=db, labbook_pk=labbook_pk,
                                     summary=summary,
                                     restored_title=title)

    return db_labbook


def update_all_lb_childelements_from_version(db: Session,
                                             labbook_childelems):
    for lb_childelem in labbook_childelems:
        elem = db.query(models.Labbookchildelement).get(
            lb_childelem['child_element_id'])
        elem.position_x = lb_childelem['position_x']
        elem.position_y = lb_childelem['position_y']
        elem.width = lb_childelem['width']
        elem.height = lb_childelem['height']
        try:
            db.commit()
        except SQLAlchemyError as e:
            logger.error(e)


def add_labbook_version(db: Session, labbook_pk, summary,
                        restored_title=None, restored_description=None):
    db_labbook = db.query(models.Labbook).get(labbook_pk)
    number = 1
    last_db_labbook_version = db.query(models.Version).filter_by(
        object_id=labbook_pk).order_by(models.Version.number.desc()).first()
    if last_db_labbook_version:
        number = last_db_labbook_version.number + 1

    if restored_title:
        db_labbook.title = restored_title
        try:
            db.commit()
        except SQLAlchemyError as e:
            logger.error(e)
        db.refresh(db_labbook)

    query = db.query(models.Labbookchildelement).filter_by(
        labbook_id=labbook_pk, deleted=False).order_by(
        models.Labbookchildelement.position_y).all()

    child_elements = []

    elem_summary = f'v{number} of labbook {db_labbook.title}'
    for elem in query:
        if elem.child_object_content_type == 30:
            child_object_version = note_version_service.add_note_version(db=db,
                                                                         note_pk=elem.child_object_id,
                                                                         summary=elem_summary)[
                1]
            note = db.query(models.Note).get(elem.child_object_id)
            child_elements.append(
                {"width": elem.width,
                 "height": elem.height,
                 "position_x": elem.position_x,
                 "position_y": elem.position_y,
                 "lab_book_id": str(elem.labbook_id),
                 "child_object_id": str(elem.child_object_id),
                 "child_element_id": str(elem.id),
                 "metadata_version": elem.version_number,
                 "child_object_version_id": str(child_object_version.id),
                 "child_object_version_number": child_object_version.number,
                 "child_object_content_type_id": child_object_version.content_type_pk,
                 'type': 'Note',
                 "content_type": note_content_type_model,
                 "display_name": note.subject,
                 "version_number": child_object_version.number,
                 "viewable": True
                 }
            )
        if elem.child_object_content_type == 40:
            child_object_version = \
                picture_version_service.add_picture_version(db=db,
                                                            picture_pk=elem.child_object_id,
                                                            summary=elem_summary)[
                    1]
            picture = db.query(models.Picture).get(elem.child_object_id)
            child_elements.append(
                {"width": elem.width,
                 "height": elem.height,
                 "position_x": elem.position_x,
                 "position_y": elem.position_y,
                 "lab_book_id": str(elem.labbook_id),
                 "child_object_id": str(elem.child_object_id),
                 "child_element_id": str(elem.id),
                 "metadata_version": elem.version_number,
                 "child_object_version_id": str(child_object_version.id),
                 "child_object_version_number": child_object_version.number,
                 "child_object_content_type_id": child_object_version.content_type_pk,
                 'type': 'Picture',
                 "content_type": picture_content_type_model,
                 "display_name": picture.title,
                 "version_number": child_object_version.number,
                 "viewable": True
                 }
            )
        if elem.child_object_content_type == 50:
            child_object_version = file_version_service.add_file_version(db=db,
                                                                         file_pk=elem.child_object_id,
                                                                         summary=elem_summary)[
                1]
            file = db.query(models.File).get(elem.child_object_id)
            child_elements.append(
                {"width": elem.width,
                 "height": elem.height,
                 "position_x": elem.position_x,
                 "position_y": elem.position_y,
                 "lab_book_id": str(elem.labbook_id),
                 "child_object_id": str(elem.child_object_id),
                 "child_element_id": str(elem.id),
                 "metadata_version": elem.version_number,
                 "child_object_version_id": str(child_object_version.id),
                 "child_object_version_number": child_object_version.number,
                 "child_object_content_type_id": child_object_version.content_type_pk,
                 'type': 'File',
                 "content_type": file_content_type_model,
                 "display_name": file.title,
                 "version_number": child_object_version.number,
                 "viewable": True
                 }
            )

    version_metadata = {
        'title': db_labbook.title,
        'description': db_labbook.description,
        'is_template': False,
        'child_elements': child_elements,
        'metadata': [],
        'projects': [],
        'metadata_version': 1
    }

    db_labbook_version = models.Version(
        object_id=labbook_pk,
        version_metadata=version_metadata,
        number=number,
        summary=summary,
        display=summary,
        content_type_pk=picture_content_type_version,
        created_at=datetime.datetime.now(),
        created_by_id=FAKE_USER_ID,
        last_modified_at=datetime.datetime.now(),
        last_modified_by_id=FAKE_USER_ID
    )

    db.add(db_labbook_version)
    db.commit()
    db.refresh(db_labbook_version)
    return db_labbook
