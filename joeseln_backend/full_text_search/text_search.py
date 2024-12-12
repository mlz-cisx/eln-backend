from sqlalchemy import or_
from joeseln_backend.models import models
from joeseln_backend.services.labbook.labbook_service import \
    check_for_labbook_access


def search_with_model(db, model, search_text, user):
    result_array = []
    if 'note' in model:
        results = db.query(models.Note).filter(
            or_(models.Note.content.like(f'%{search_text}%'),
                models.Note.subject.like(f'%{search_text}%'))).all()

        for result in results:
            lb_elem = db.query(models.Labbookchildelement).get(result.elem_id)
            if check_for_labbook_access(db=db, labbook_pk=lb_elem.labbook_id,
                                        user=user):
                created_by = db.query(models.User).get(
                    lb_elem.created_by_id)
                res_dic = {'content_type_model': 'shared_elements.note',
                           'display': result.subject,
                           'created_by': created_by,
                           'pk': str(lb_elem.labbook_id),
                           'labbook_pos_y': lb_elem.position_y,
                           'element_pk': str(result.id)}
                result_array.append(res_dic)
        # subject content
    if 'file' in model:
        results = db.query(models.File).filter(
            or_(models.File.title.like(f'%{search_text}%'),
                models.File.description.like(f'%{search_text}%'))).all()
        for result in results:
            lb_elem = db.query(models.Labbookchildelement).get(result.elem_id)
            if check_for_labbook_access(db=db, labbook_pk=lb_elem.labbook_id,
                                        user=user):
                created_by = db.query(models.User).get(
                    lb_elem.created_by_id)
                res_dic = {'content_type_model': 'shared_elements.file',
                           'display': result.title,
                           'created_by': created_by,
                           'pk': str(lb_elem.labbook_id),
                           'labbook_pos_y': lb_elem.position_y,
                           'element_pk': str(result.id)}
                result_array.append(res_dic)
        # title description
    if 'picture' in model:
        results = db.query(models.Picture).filter(
            or_(models.Picture.title.like(f'%{search_text}%'))).all()
        for result in results:
            lb_elem = db.query(models.Labbookchildelement).get(result.elem_id)
            if check_for_labbook_access(db=db, labbook_pk=lb_elem.labbook_id,
                                        user=user):
                created_by = db.query(models.User).get(
                    lb_elem.created_by_id)
                res_dic = {'content_type_model': 'pictures.picture',
                           'display': result.title,
                           'created_by': created_by,
                           'pk': str(lb_elem.labbook_id),
                           'labbook_pos_y': lb_elem.position_y,
                           'element_pk': str(result.id)}
                result_array.append(res_dic)

        # title
    if 'labbook' in model:
        results = db.query(models.Labbook).filter(
            or_(models.Labbook.title.like(f'%{search_text}%'),
                models.Labbook.description.like(f'%{search_text}%'))).all()

        for result in results:
            if check_for_labbook_access(db=db, labbook_pk=result.id,
                                        user=user):
                created_by = db.query(models.User).get(
                    result.created_by_id)
                res_dic = {'content_type_model': 'labbooks.labbook',
                           'display': result.title,
                           'created_by': created_by,
                           'pk': str(result.id),
                           'labbook_pos_y': 0,
                           'element_pk': str(result.id)}
                result_array.append(res_dic)

    return result_array
