import datetime

from sqlalchemy.orm import Session

from joeseln_backend.models import models


def shift_elements_after_restore(
        db: Session,
        labbook_id,
        restored_row: int,
        restored_height: int,
        restored_width: int,
        user
):
    # Base filters: same as in create_lb_childelement_row
    base_filters = [
        models.Labbookchildelement.labbook_id == labbook_id,
        models.Labbookchildelement.deleted.is_(False),
        models.Labbookchildelement.position_x < restored_width,
    ]

    # Find first overlapping element
    first_elem = (
        db.query(models.Labbookchildelement)
        .filter(
            *base_filters,
            (models.Labbookchildelement.position_y +
             models.Labbookchildelement.height) > restored_row,
            models.Labbookchildelement.position_y <
            (restored_row + restored_height),
        )
        .order_by(models.Labbookchildelement.position_y)
        .first()
    )

    # Determine the actual insertion Y
    position_below = restored_row
    overlaps = first_elem and (first_elem.position_y - restored_row) <= 0

    if overlaps:
        position_below = first_elem.position_y + first_elem.height

    # Query all elements below
    query = []
    if first_elem:
        query = (
            db.query(models.Labbookchildelement)
            .filter(
                *base_filters,
                (models.Labbookchildelement.position_y +
                 models.Labbookchildelement.height) > position_below,
            )
            .order_by(models.Labbookchildelement.position_y)
            .all()
        )

    # Calculate delta
    delta = query[0].position_y - position_below if query else 0

    # Shift all elements down
    for elem in query:
        elem.position_y += restored_height - delta
        elem.last_modified_at = datetime.datetime.now()
        elem.last_modified_by_id = user.id

    db.commit()

    return position_below
