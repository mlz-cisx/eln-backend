from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from joeseln_backend.models import models
from joeseln_backend.services.labbookchildelements.labbookchildelement_schemas import *
from joeseln_backend.ws.ws_client import transmit
from joeseln_backend.services.picture import picture_service
from joeseln_backend.services.file import file_service
from joeseln_backend.auth import security
from joeseln_backend.conf.mocks.mock_user import FAKE_USER_ID

from joeseln_backend.mylogging.root_logger import logger


def map_to_child_object_model(child_object_content_type):
    if child_object_content_type == 30:
        return 'shared_elements.note'
    if child_object_content_type == 40:
        return 'pictures.picture'
    if child_object_content_type == 50:
        return 'shared_elements.file'


def get_lb_childelements(db: Session, labbook_pk, as_export):
    query = db.query(models.Labbookchildelement).filter_by(
        labbook_id=labbook_pk, deleted=False).order_by(
        models.Labbookchildelement.position_y).all()

    user = security._authenticate_user(security.fake_users_db, 'johndoe',
                                      'secret')
    access_token_expires = security.timedelta(
        minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    for elem in query:
        if elem.child_object_content_type == 30:
            elem.child_object = db.query(models.Note).get(elem.child_object_id)
            db.close()
        if elem.child_object_content_type == 40:
            elem.child_object = picture_service.get_picture_in_lb_init(db=db,
                                                                       picture_pk=elem.child_object_id,
                                                                       access_token=access_token,
                                                                       as_export=as_export)

        if elem.child_object_content_type == 50:
            elem.child_object = file_service.get_file(db=db,
                                                      file_pk=elem.child_object_id)

    return query


def patch_lb_childelement(db: Session, labbook_pk, element_pk,
                          labbook_childelem,
                          ):
    db_labbook_elem = db.query(models.Labbookchildelement).get(element_pk)
    db_labbook_elem.position_x = labbook_childelem.position_x
    db_labbook_elem.position_y = labbook_childelem.position_y
    db_labbook_elem.width = labbook_childelem.width
    db_labbook_elem.height = labbook_childelem.height
    db_labbook_elem.last_modified_at = datetime.datetime.now()
    db_labbook_elem.last_modified_by_id = FAKE_USER_ID

    lb_to_update = db.query(models.Labbook).get(db_labbook_elem.labbook_id)
    lb_to_update.last_modified_at = datetime.datetime.now()
    lb_to_update.last_modified_by_id = FAKE_USER_ID

    try:
        db.commit()
    except SQLAlchemyError as e:
        logger.error(e)

    db.refresh(db_labbook_elem)

    if db_labbook_elem.child_object_content_type == 30:
        db_labbook_elem.child_object = db.query(models.Note).get(
            db_labbook_elem.child_object_id)
    if db_labbook_elem.child_object_content_type == 40:
        db_labbook_elem.child_object = picture_service.get_picture(db=db,
                                                                   picture_pk=db_labbook_elem.child_object_id)

    if db_labbook_elem.child_object_content_type == 50:
        db_labbook_elem.child_object = file_service.get_file(db=db,
                                                             file_pk=db_labbook_elem.child_object_id)

    try:
        transmit({'model_name': 'labbook_patch', 'model_pk': str(labbook_pk)})
    except RuntimeError as e:
        logger.error(e)

    return db_labbook_elem


def create_lb_childelement(db: Session, labbook_pk,
                           labbook_childelem: Labbookchildelement_Create):
    db_labbook_elem = models.Labbookchildelement(
        labbook_id=labbook_pk,
        position_x=labbook_childelem.position_x,
        position_y=labbook_childelem.position_y,
        width=labbook_childelem.width,
        height=labbook_childelem.height,
        child_object_id=labbook_childelem.child_object_id,
        child_object_content_type=labbook_childelem.child_object_content_type,
        child_object_content_type_model=map_to_child_object_model(
            child_object_content_type=labbook_childelem.child_object_content_type),
        version_number=0,
        created_at=datetime.datetime.now(),
        created_by_id=FAKE_USER_ID,
        last_modified_at=datetime.datetime.now(),
        last_modified_by_id=FAKE_USER_ID
    )
    db.add(db_labbook_elem)

    lb_to_update = db.query(models.Labbook).get(labbook_pk)
    lb_to_update.last_modified_at = datetime.datetime.now()
    lb_to_update.last_modified_by_id = FAKE_USER_ID

    try:
        db.commit()
    except SQLAlchemyError as e:
        logger.error(e)

    update_child_element(db_labbook_elem=db_labbook_elem,
                         child_object_content_type=db_labbook_elem.child_object_content_type,
                         child_object_id=db_labbook_elem.child_object_id,
                         db=db)

    db.refresh(db_labbook_elem)

    if db_labbook_elem.child_object_content_type == 30:
        db_labbook_elem.child_object = db.query(models.Note).get(
            db_labbook_elem.child_object_id)
    if db_labbook_elem.child_object_content_type == 40:
        db_labbook_elem.child_object = picture_service.get_picture(db=db,
                                                                   picture_pk=db_labbook_elem.child_object_id)

    if db_labbook_elem.child_object_content_type == 50:
        db_labbook_elem.child_object = file_service.get_file(db=db,
                                                             file_pk=db_labbook_elem.child_object_id)

    try:
        transmit({'model_name': 'labbook', 'model_pk': str(labbook_pk)})
    except RuntimeError as e:
        logger.error(e)

    return db_labbook_elem


def update_all_lb_childelements(db: Session,
                                labbook_childelems, labbook_pk):
    for lb_childelem in labbook_childelems:
        elem = db.query(models.Labbookchildelement).get(lb_childelem.id)
        elem.position_x = lb_childelem.position_x
        elem.position_y = lb_childelem.position_y
        elem.width = lb_childelem.width
        elem.height = lb_childelem.height
        elem.last_modified_at = datetime.datetime.now()
        elem.last_modified_by_id = FAKE_USER_ID
        try:
            db.commit()
        except SQLAlchemyError as e:
            logger.error(e)
    # event listener not working with bulk
    # db.bulk_update_mappings(models.Labbookchildelement(), labbook_childelems)
    try:
        db.commit()
    except SQLAlchemyError as e:
        logger.error(e)
        return

    try:
        transmit({'model_name': 'labbook', 'model_pk': str(labbook_pk)})
    except RuntimeError as e:
        logger.error(e)


def update_child_element(db_labbook_elem, child_object_content_type,
                         child_object_id, db):
    if child_object_content_type == 30:
        note = db.query(models.Note).get(child_object_id)
        note.elem_id = db_labbook_elem.id
        try:
            db.commit()
        except SQLAlchemyError as e:
            logger.error(e)

    if child_object_content_type == 40:
        picture = db.query(models.Picture).get(child_object_id)
        picture.elem_id = db_labbook_elem.id
        try:
            db.commit()
        except SQLAlchemyError as e:
            logger.error(e)

    if child_object_content_type == 50:
        file = db.query(models.File).get(child_object_id)
        file.elem_id = db_labbook_elem.id
        try:
            db.commit()
        except SQLAlchemyError as e:
            logger.error(e)
