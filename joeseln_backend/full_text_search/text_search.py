from sqlalchemy import or_
from typesense.client import Client
from joeseln_backend.models import models
from joeseln_backend.services.labbook.labbook_service import \
    check_for_labbook_access
from joeseln_backend.conf.base_conf import LABBOOK_QUERY_MODE
from joeseln_backend.services.user_to_group.user_to_group_service import get_user_groups
def search_with_model(db, model, search_text, user, typesense: Client):
    result_array = []
    # query for labbook_id that user has access right
    user_groups = get_user_groups(db=db, username=user.username)
    lbs = []
    if LABBOOK_QUERY_MODE == 'match':
        lbs = db.query(models.Labbook).filter(
            or_(*[models.Labbook.title.contains(name) for name in
            user_groups])).all()
    else:
        lbs = db.query(models.Labbook).filter(
        models.Labbook.title.in_(user_groups)).all()
    labbook_ids = [str(lb.id) for lb in lbs]
    
    if 'note' in model:
        search_parameters = {
            'q': search_text,
            'filter_by': f"labbook_id:[{','.join(labbook_ids)}] && soft_delete:=false",  # filter for notebook that user can access
            'query_by': 'subject,content',
            'fuzzy': True
        }
        
        search_res = typesense.collections['notes'].documents.search(search_parameters)['hits']
        for result in search_res:
            result = result["document"]
            lb_elem = db.query(models.Labbookchildelement).get(result["elem_id"])
            created_by = db.query(models.User).get(lb_elem.created_by_id)
            res_dic = {'content_type_model': 'shared_elements.note',
                           'display': result["subject"],
                           'created_by': created_by,
                           'pk': str(lb_elem.labbook_id),
                           'labbook_pos_y': lb_elem.position_y,
                           'element_pk': str(result["id"])}
            result_array.append(res_dic)
 
        # subject content
    if 'file' in model:
        results = db.query(models.File).filter(
            or_(models.File.title.like(f'%{search_text}%'),
                models.File.description.like(f'%{search_text}%'))).all()
        for result in results:
            lb_elem = db.query(models.Labbookchildelement).get(result.elem_id)
            if lb_elem.labbook_id in labbook_ids:
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
            if lb_elem.labbook_id in labbook_ids:
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
