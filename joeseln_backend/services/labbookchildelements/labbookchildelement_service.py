import datetime

from sqlalchemy import and_, func, select, literal, or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, aliased
from typesense import Client
from typesense.exceptions import TypesenseClientError

from joeseln_backend.full_text_search.html_stripper import strip_html_and_binary
from joeseln_backend.helper import db_ordering
from joeseln_backend.models import models
from joeseln_backend.mylogging.root_logger import logger
from joeseln_backend.services.file import file_service
from joeseln_backend.services.file.file_service import (
    get_file_related_comments_count,
    get_file_relations,
)
from joeseln_backend.services.labbook.labbook_service import (
    check_for_labbook_access,
    check_for_labbook_admin_access,
)
from joeseln_backend.services.labbookchildelements.labbookchildelement_schemas import (
    Labbookchildelement_Create,
    Labbookchildelement_CreateRow,
    Labbookchildelement_PatchHeight,
)
from joeseln_backend.services.note.note_service import (
    get_note,
    get_note_related_comments_count,
    get_note_relations,
)
from joeseln_backend.services.picture import picture_service
from joeseln_backend.services.picture.picture_service import (
    get_picture,
    get_picture_related_comments_count,
    get_picture_relations,
)
from joeseln_backend.ws.events import transmit


def map_to_child_object_model(child_object_content_type):
    if child_object_content_type == 30:
        return 'shared_elements.note'
    if child_object_content_type == 40:
        return 'pictures.picture'
    if child_object_content_type == 50:
        return 'shared_elements.file'


def get_lb_childelements_for_export(db: Session, labbook_pk, access_token, user,
                                    as_export):
    query = db.query(models.Labbookchildelement).filter_by(
        labbook_id=labbook_pk, deleted=False).order_by(
        models.Labbookchildelement.position_y).all()

    for elem in query:
        if elem.child_object_content_type == 30:
            elem.child_object = get_note(db=db, note_pk=elem.child_object_id)
            elem.relations = get_note_relations(db=db,
                                                note_pk=elem.child_object_id,
                                                params='',
                                                user=user)

        if elem.child_object_content_type == 40:
            elem.child_object = picture_service.get_picture_for_export(db=db,
                                                                       picture_pk=elem.child_object_id)
            elem.relations = get_picture_relations(db=db,
                                                   picture_pk=elem.child_object_id,
                                                   params='',
                                                   user=user)

        if elem.child_object_content_type == 50:
            elem.child_object = file_service.get_file(db=db,
                                                      file_pk=elem.child_object_id,
                                                      user=user)

            elem.relations = get_file_relations(db=db,
                                                file_pk=elem.child_object_id,
                                                params='', user=user)

    return query


def get_lb_childelements_for_zip_export(db: Session, labbook_pk, user,
                                        as_export):
    query = db.query(models.Labbookchildelement).filter_by(
        labbook_id=labbook_pk, deleted=False).order_by(
        models.Labbookchildelement.position_y).all()

    for elem in query:
        if elem.child_object_content_type == 30:
            elem.child_object = db.get(models.Note, elem.child_object_id)
            elem.relations = get_note_relations(db=db,
                                                note_pk=elem.child_object_id,
                                                params='',
                                                user=user)

        if elem.child_object_content_type == 40:
            elem.child_object = picture_service.get_picture_for_zip_export(
                db=db,
                picture_pk=elem.child_object_id)

            elem.relations = get_picture_relations(db=db,
                                                   picture_pk=elem.child_object_id,
                                                   params='',
                                                   user=user)

        if elem.child_object_content_type == 50:
            elem.child_object = file_service.get_file_for_zip_export(db=db,
                                                                     file_pk=elem.child_object_id,
                                                                     user=user)

            elem.relations = get_file_relations(db=db,
                                                file_pk=elem.child_object_id,
                                                params='', user=user)

    return query


def get_lb_childelements_from_user(db: Session, labbook_pk, as_export, user):
    if not check_for_labbook_access(db=db, labbook_pk=labbook_pk, user=user):
        return None
    db_labbook = db.query(models.Labbook).get(labbook_pk)
    if db_labbook is None:
        return None

    # uncorrelated subquery to get comment count
    related_comments_count = (
        select(models.Relation.right_object_id, func.count().label('count'))
        .where(
            and_(
                models.Relation.left_content_type == 70,
                models.Relation.deleted == False,
            )
        )
        .group_by(models.Relation.right_object_id)
        .alias('num_related_comment')
    )

    elem = models.Labbookchildelement
    query = (
        select(
            *elem.__table__.columns,
            func.coalesce(related_comments_count.c.count, 0).label('num_related_comments'),
        )
        .outerjoin(
            related_comments_count,
            elem.child_object_id == related_comments_count.c.right_object_id,
        )
        .where(
            and_(elem.labbook_id == labbook_pk, elem.deleted == False)
        )
        .order_by(elem.position_y)
    )
    return db.execute(query).mappings().all()


def get_lb_childelements_from_user_for_tableview(
        db: Session,
        labbook_id,
        params,
        user
):
    if not check_for_labbook_access(
            db=db,
            labbook_pk=labbook_id,
            user=user
    ):
        return None

    db_labbook = db.query(models.Labbook).get(labbook_id)
    if db_labbook is None:
        return None

    order_params = db_ordering.get_order_params(
        ordering=params.get("ordering")
    )

    search_text = params.get("search")
    deleted = False

    #
    # FILES
    #
    file_created_user = aliased(models.User)
    file_modified_user = aliased(models.User)

    file_query = (
        db.query(
            models.File.id.label("entity_id"),
            literal("file").label("entity_type"),
            models.File.title.label("title"),
            models.File.created_at.label("created_at"),
            models.File.last_modified_at.label("last_modified_at"),

            file_created_user.username.label("created_by"),
            file_modified_user.username.label("last_modified_by"),

            models.Labbook.title.label("labbook_title"),
        )
        .join(
            models.Labbookchildelement,
            models.File.elem_id == models.Labbookchildelement.id,
        )
        .join(
            models.Labbook,
            models.Labbook.id == models.Labbookchildelement.labbook_id,
        )
        .outerjoin(
            file_created_user,
            file_created_user.id == models.File.created_by_id,
        )
        .outerjoin(
            file_modified_user,
            file_modified_user.id == models.File.last_modified_by_id,
        )
        .filter(
            models.File.deleted == deleted,
            models.Labbook.deleted == False,
            models.Labbookchildelement.labbook_id == labbook_id,
        )
    )

    if search_text:
        search_term = f"%{search_text.strip()}%"
        file_query = file_query.filter(
            or_(
                models.File.title.ilike(search_term),
                file_created_user.username.ilike(search_term),
                file_modified_user.username.ilike(search_term),
                literal("file").ilike(search_term),
            )
        )

    #
    # NOTES
    #
    note_created_user = aliased(models.User)
    note_modified_user = aliased(models.User)

    note_query = (
        db.query(
            models.Note.id.label("entity_id"),
            literal("note").label("entity_type"),
            models.Note.subject.label("title"),
            models.Note.created_at.label("created_at"),
            models.Note.last_modified_at.label("last_modified_at"),

            note_created_user.username.label("created_by"),
            note_modified_user.username.label("last_modified_by"),

            models.Labbook.title.label("labbook_title"),
        )
        .join(
            models.Labbookchildelement,
            models.Note.elem_id == models.Labbookchildelement.id,
        )
        .join(
            models.Labbook,
            models.Labbook.id == models.Labbookchildelement.labbook_id,
        )
        .outerjoin(
            note_created_user,
            note_created_user.id == models.Note.created_by_id,
        )
        .outerjoin(
            note_modified_user,
            note_modified_user.id == models.Note.last_modified_by_id,
        )
        .filter(
            models.Note.deleted == deleted,
            models.Labbook.deleted == False,
            models.Labbookchildelement.labbook_id == labbook_id,
        )
    )

    if search_text:
        search_term = f"%{search_text.strip()}%"
        note_query = note_query.filter(
            or_(
                models.Note.subject.ilike(search_term),
                note_created_user.username.ilike(search_term),
                note_modified_user.username.ilike(search_term),
                literal("note").ilike(search_term),
            )
        )

    #
    # PICTURES
    #
    picture_created_user = aliased(models.User)
    picture_modified_user = aliased(models.User)

    picture_query = (
        db.query(
            models.Picture.id.label("entity_id"),
            literal("picture").label("entity_type"),
            models.Picture.title.label("title"),
            models.Picture.created_at.label("created_at"),
            models.Picture.last_modified_at.label("last_modified_at"),

            picture_created_user.username.label("created_by"),
            picture_modified_user.username.label("last_modified_by"),

            models.Labbook.title.label("labbook_title"),
        )
        .join(
            models.Labbookchildelement,
            models.Picture.elem_id == models.Labbookchildelement.id,
        )
        .join(
            models.Labbook,
            models.Labbook.id == models.Labbookchildelement.labbook_id,
        )
        .outerjoin(
            picture_created_user,
            picture_created_user.id == models.Picture.created_by_id,
        )
        .outerjoin(
            picture_modified_user,
            picture_modified_user.id == models.Picture.last_modified_by_id,
        )
        .filter(
            models.Picture.deleted == deleted,
            models.Labbook.deleted == False,
            models.Labbookchildelement.labbook_id == labbook_id,
        )
    )

    if search_text:
        search_term = f"%{search_text.strip()}%"
        picture_query = picture_query.filter(
            or_(
                models.Picture.title.ilike(search_term),
                picture_created_user.username.ilike(search_term),
                picture_modified_user.username.ilike(search_term),
                literal("picture").ilike(search_term),
            )
        )

    #
    # UNION ALL
    #
    union_subquery = (
        file_query
        .union_all(note_query)
        .union_all(picture_query)
        .subquery()
    )

    merged = select(
        union_subquery.c[0].label("entity_id"),
        union_subquery.c[1].label("entity_type"),
        union_subquery.c[2].label("title"),
        union_subquery.c[3].label("created_at"),
        union_subquery.c[4].label("last_modified_at"),
        union_subquery.c[5].label("created_by"),
        union_subquery.c[6].label("last_modified_by"),
        union_subquery.c[7].label("labbook_title"),
    ).subquery("merged")


    #
    # ORDERING
    #
    column_name, direction = order_params.split()

    order_mapping = {
        "title": merged.c.title,
        "created_at": merged.c.created_at,
        "created_by": merged.c.created_by,
        "last_modified_at": merged.c.last_modified_at,
        "last_modified_by": merged.c.last_modified_by,
        "entity_type": merged.c.entity_type,
    }

    column = order_mapping.get(column_name)

    if column is None:
        order_column = merged.c.created_at.desc()
    elif direction.lower() == "desc":
        order_column = column.desc()
    else:
        order_column = column.asc()

    rows = (
        db.query(merged)
        .order_by(order_column)
        .offset(params.get("offset", 0))
        .limit(params.get("limit", 20))
        .all()
    )

    return rows


def check_for_version_edit_access_on_lb_elem(db: Session, lb_elem, user):
    elem_creator = db.get(models.User, lb_elem.created_by_id)
    # lowest rights
    if not elem_creator.admin:
        return True
    else:
        return check_for_labbook_admin_access(db=db,
                                              labbook_pk=lb_elem.labbook_id,
                                              user=user)


def create_lb_childelement(db: Session, labbook_pk,
                           labbook_childelem: Labbookchildelement_Create, user,
                           typesense: Client, cloned=None):
    if check_for_labbook_access(db=db, labbook_pk=labbook_pk,
                                user=user) != "Write":
        return None

    existing = (
        db.query(models.Labbookchildelement)
        .filter(
            models.Labbookchildelement.child_object_id == labbook_childelem.child_object_id)
        .first()
    )

    if existing:
        # already exists
        return None


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
        created_by_id=user.id,
    )
    db.add(db_labbook_elem)

    lb_to_update = db.get(models.Labbook, labbook_pk)
    lb_to_update.last_modified_at = datetime.datetime.now()
    lb_to_update.last_modified_by_id = user.id

    try:
        db.commit()
    except SQLAlchemyError as e:
        logger.error(e)
        db.close()
        return db_labbook_elem

    update_child_element(db_labbook_elem=db_labbook_elem,
                         child_object_content_type=db_labbook_elem.child_object_content_type,
                         child_object_id=db_labbook_elem.child_object_id,
                         db=db)

    db.refresh(db_labbook_elem)

    if db_labbook_elem.child_object_content_type == 30:
        note = get_note(db=db, note_pk=db_labbook_elem.child_object_id)
        db_labbook_elem.child_object = note
        db_labbook_elem.num_related_comments = get_note_related_comments_count(
            db=db,
            note_pk=db_labbook_elem.child_object_id, user=user)
        try:
            # insert note to typesense for searching purpose
            stripped_content = strip_html_and_binary(note.content)
            typesense.collections['notes'].documents.upsert({'id': str(note.id),
                                                            'elem_id': str(db_labbook_elem.id),
                                                            'subject': note.subject, 
                                                            'content': stripped_content, 
                                                            'last_modified_at': int(note.last_modified_at.timestamp()),
                                                            'labbook_id': str(labbook_pk),
                                                            'soft_delete': False})
        except TypesenseClientError as e:
            logger.error(e)

    if db_labbook_elem.child_object_content_type == 40:
        pic = get_picture(db=db, picture_pk=db_labbook_elem.child_object_id, user=user)
        db_labbook_elem.child_object = picture_service.get_picture(db=db,
                                                                   picture_pk=db_labbook_elem.child_object_id,
                                                                   user=user)
        db_labbook_elem.num_related_comments = get_picture_related_comments_count(
            db=db, picture_pk=db_labbook_elem.child_object_id, user=user)
        try:
            # insert picture title to typesense for searching purpose
            typesense.collections['pictures'].documents.upsert({'id': str(pic.id),
                                                            'elem_id': str(db_labbook_elem.id),
                                                            'subject': pic.title,
                                                            'content': '',
                                                            'last_modified_at': int(pic.last_modified_at.timestamp()),
                                                            'labbook_id': str(labbook_pk),
                                                            'soft_delete': False})
        except TypesenseClientError as e:
            logger.error(e)

    if db_labbook_elem.child_object_content_type == 50:
        file_service.update_file_typesense(
            db.get(models.File, db_labbook_elem.child_object_id),
            db_labbook_elem, typesense,
        )
        db_labbook_elem.child_object = file_service.get_file(db=db,
                                                             file_pk=db_labbook_elem.child_object_id,
                                                             user=user)
        db_labbook_elem.num_related_comments = get_file_related_comments_count(
            db=db,
            file_pk=db_labbook_elem.child_object_id, user=user)

    if not cloned:
        try:
            transmit({'model_name': 'labbook', 'model_pk': str(labbook_pk)})
        except RuntimeError as e:
            logger.error(e)

    return db_labbook_elem


def patch_lb_childelement_height(db: Session, labbook_pk,
                                 element_pk,
                                 labbook_childelem: Labbookchildelement_PatchHeight,
                                 user):
    if check_for_labbook_access(db=db, labbook_pk=labbook_pk,
                                user=user) != "Write":
        return None
    lb_elem = db.get(models.Labbookchildelement, element_pk)
    if lb_elem is None or lb_elem.labbook_id != labbook_pk:
        return None
    lb_elem.height = labbook_childelem.height
    try:
        db.commit()
    except SQLAlchemyError as e:
        logger.error(e)
        db.close()
        return "nok"
    try:
        transmit({'model_name': 'labbook', 'model_pk': str(labbook_pk)})
    except RuntimeError as e:
        logger.error(e)
    return "ok"


def create_lb_childelement_bottom(
        db: Session,
        labbook_pk,
        labbook_childelem: Labbookchildelement_CreateRow,
        user,
        typesense: Client,
):
    # first avaliable position_y
    posY = (
        db.query(
            func.max(
                models.Labbookchildelement.position_y
                + models.Labbookchildelement.height
            )
        )
        .filter(
            models.Labbookchildelement.labbook_id == labbook_pk,
            models.Labbookchildelement.deleted == False,
        )
        .scalar()
    )

    posY = 0 if posY is None else posY

    elem = Labbookchildelement_Create(
        position_x=0,
        position_y=posY,
        height=labbook_childelem.height,
        width=labbook_childelem.width,
        child_object_id=labbook_childelem.child_object_id,
        child_object_content_type=labbook_childelem.child_object_content_type,
    )

    return create_lb_childelement(db, labbook_pk, elem, user, typesense,
                                  cloned=labbook_childelem.cloned)


def create_lb_childelement_row(
        db: Session,
        labbook_pk,
        labbook_childelem: Labbookchildelement_CreateRow,
        user,
        typesense: Client,
):
    raw_pos = labbook_childelem.position

    if raw_pos in (None, "top"):
        position = 0
    elif raw_pos == "bottom":
        return create_lb_childelement_bottom(db=db,
                                             labbook_pk=labbook_pk,
                                             labbook_childelem=labbook_childelem,
                                             user=user,
                                             typesense=typesense)
    else:
        position = int(raw_pos)

    # Base query filters
    base_filters = [
        models.Labbookchildelement.labbook_id == labbook_pk,
        models.Labbookchildelement.deleted.is_(False),
        models.Labbookchildelement.position_x < labbook_childelem.width,
    ]

    # Find the first overlapping element
    first_elem = (
        db.query(models.Labbookchildelement)
        .filter(
            *base_filters,
            (
                    models.Labbookchildelement.position_y + models.Labbookchildelement.height) > position,
            models.Labbookchildelement.position_y < (
                    labbook_childelem.height + position),
        )
        .order_by(models.Labbookchildelement.position_y)
        .first()
    )

    # Determine position below
    position_below = position
    overlaps = first_elem and (first_elem.position_y - position) <= 0
    if overlaps:
        position_below = (
            first_elem.position_y
            if raw_pos == "top"
            else first_elem.position_y + first_elem.height
        )

    # Query elements below
    query = []
    if first_elem:
        query = (
            db.query(models.Labbookchildelement)
            .filter(
                *base_filters,
                (
                        models.Labbookchildelement.position_y + models.Labbookchildelement.height) > position_below,
            )
            .order_by(models.Labbookchildelement.position_y)
            .all()
        )

    # Calculate delta
    delta = query[0].position_y - position_below if query else 0

    # Adjust positions
    for elem in query:
        elem.position_y += labbook_childelem.height - delta

    try:
        db.commit()
    except SQLAlchemyError as e:
        logger.error(e)
        db.close()

        return False

    elem = Labbookchildelement_Create(
        position_x=0,
        position_y=position_below,
        height=labbook_childelem.height,
        width=labbook_childelem.width,
        child_object_id=labbook_childelem.child_object_id,
        child_object_content_type=labbook_childelem.child_object_content_type,
    )

    return create_lb_childelement(db, labbook_pk, elem, user, typesense)


def update_all_lb_childelements(db: Session,
                                labbook_childelems, labbook_pk, user):
    if not check_for_labbook_access(db=db, labbook_pk=labbook_pk, user=user):
        return

    update_data = [{
        'id': lb_childelem.id,
        'position_x': lb_childelem.position_x,
        'position_y': lb_childelem.position_y,
        'width': lb_childelem.width,
        'height': lb_childelem.height,
    } for lb_childelem in labbook_childelems]

    db.bulk_update_mappings(models.Labbookchildelement, update_data)

    try:
        db.commit()
    except SQLAlchemyError as e:
        logger.error(e)
        db.close()
        return

    transmit({'model_name': 'labbook', 'model_pk': str(labbook_pk)})

    return True


def update_child_element(db_labbook_elem, child_object_content_type,
                         child_object_id, db):
    if child_object_content_type == 30:
        note = db.get(models.Note, child_object_id)
        note.elem_id = db_labbook_elem.id
        try:
            db.commit()
        except SQLAlchemyError as e:
            logger.error(e)
            db.close()

    if child_object_content_type == 40:
        picture = db.get(models.Picture, child_object_id)
        picture.elem_id = db_labbook_elem.id
        try:
            db.commit()
        except SQLAlchemyError as e:
            logger.error(e)
            db.close()

    if child_object_content_type == 50:
        file = db.get(models.File, child_object_id)
        file.elem_id = db_labbook_elem.id
        try:
            db.commit()
        except SQLAlchemyError as e:
            logger.error(e)
            db.close()
