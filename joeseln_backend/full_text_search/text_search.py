from sqlalchemy import func, or_, and_
from typesense.client import Client
from typing_extensions import TypedDict

from joeseln_backend.conf.base_conf import LABBOOK_QUERY_MODE
from joeseln_backend.models import models
from joeseln_backend.services.labbook.labbook_service import \
    check_for_labbook_access
from joeseln_backend.services.user.user_schema import UserExtended
from joeseln_backend.services.user_to_group.user_to_group_service import \
    get_user_groups


def encode_umlauts_to_html(text):
    replacements = {
        'ä': '&auml;',
        'ö': '&ouml;',
        'ü': '&uuml;',
        'Ä': '&Auml;',
        'Ö': '&Ouml;',
        'Ü': '&Uuml;',
        'ß': '&szlig;',
    }
    for char, entity in replacements.items():
        text = text.replace(char, entity)
    return text


class search_result_type(TypedDict):
    content_type_model: str
    display: str
    created_by: UserExtended
    pk: str
    labbook_pos_y: int
    element_pk: str


class lb_search_result_type(TypedDict):
    content_type_model: str
    labbook_pos_y: int
    element_pk: str


def search_with_model(db, model, search_text, user, typesense: Client):
    result_array = []
    # query for labbook_id that user has access right
    user_groups = get_user_groups(db=db, username=user.username)
    if LABBOOK_QUERY_MODE == 'match':
        lbs = db.query(models.Labbook).filter(
            or_(*[models.Labbook.title.contains(name) for name in
                  user_groups]), models.Labbook.deleted == False).all()
    else:
        lbs = db.query(models.Labbook).filter(
            models.Labbook.title.in_(user_groups),
            models.Labbook.deleted == False).all()
    labbook_ids = [str(lb.id) for lb in lbs]

    if 'note' in model:
        search_queries = []
        search_queries.append({
            'collection': 'notes',
            'q': search_text,
            'filter_by': f"labbook_id:[{','.join(labbook_ids)}] && soft_delete:=false",
            'query_by': 'subject,content',
            'fuzzy': True,
            'limit': 250
        })
        search_res = typesense.multi_search.perform(
            {'searches': search_queries},
            {}
        )['results'][0]['hits']

        for result in search_res:
            result = result["document"]
            lb_elem = db.query(models.Labbookchildelement).get(
                result["elem_id"])
            if lb_elem:
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
        encoded_search_text = encode_umlauts_to_html(search_text)
        cleaned_f = func.regexp_replace(
            func.regexp_replace(
                func.regexp_replace(
                    models.File.description,
                    r'data:([a-zA-Z0-9]+/[a-zA-Z0-9.+-]+);base64,[A-Za-z0-9+/=]+',
                    '',
                    'g'
                ),
                r'&nbsp;',
                ' ',
                'g'
            ),
            r'<[^>]+>',
            '',
            'g'
        )

        results = db.query(models.File).filter(
            or_(models.File.title.ilike(f'%{search_text}%'),
                func.lower(cleaned_f).ilike(
                    f'%{encoded_search_text.lower()}%'))).all()

        for result in results:
            lb_elem = db.query(models.Labbookchildelement).get(result.elem_id)
            if lb_elem and str(lb_elem.labbook_id) in labbook_ids:
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
        search_queries = []
        search_queries.append({
            'collection': 'pictures',
            'q': search_text,
            'filter_by': f"labbook_id:[{','.join(labbook_ids)}] && soft_delete:=false",
            'query_by': 'subject,content',
            'fuzzy': True,
            'limit': 250
        })
        search_res = typesense.multi_search.perform(
            {'searches': search_queries},
            {}
        )['results'][0]['hits']

        for result in search_res:
            result = result["document"]
            lb_elem = db.query(models.Labbookchildelement).get(
                result["elem_id"])
            if lb_elem:
                created_by = db.query(models.User).get(lb_elem.created_by_id)
                res_dic = {
                    "content_type_model": "pictures.picture",
                    "display": result["subject"],
                    "created_by": created_by,
                    "pk": str(lb_elem.labbook_id),
                    "labbook_pos_y": lb_elem.position_y,
                    "element_pk": str(result["id"]),
                }
                result_array.append(res_dic)

    if 'labbook' in model:
        encoded_search_text = encode_umlauts_to_html(search_text)
        cleaned_l = func.regexp_replace(
            func.regexp_replace(
                func.regexp_replace(
                    models.Labbook.description,
                    r'data:([a-zA-Z0-9]+/[a-zA-Z0-9.+-]+);base64,[A-Za-z0-9+/=]+',
                    '',
                    'g'
                ),
                r'&nbsp;',
                ' ',
                'g'
            ),
            r'<[^>]+>',
            '',
            'g'
        )

        results = db.query(models.Labbook).filter(
            or_(models.Labbook.title.ilike(f'%{search_text}%'),
                func.lower(cleaned_l).ilike(f'%{encoded_search_text.lower()}%')
                )).all()

        for result in results:
            if str(result.id) in labbook_ids:
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


def search_in_labbook(db, labbook_pk, search_text, user, typesense: Client):
    if not check_for_labbook_access(
            db=db, labbook_pk=labbook_pk, user=user):
        return None

    result_array = []
    labbook_id = str(labbook_pk)

    search_res = typesense_search_all(
        typesense=typesense,
        collection="notes",
        search_text=search_text,
        labbook_id=labbook_id,
    )

    for result in search_res:
        result = result["document"]
        lb_elem = db.query(models.Labbookchildelement).get(
            result["elem_id"])
        if lb_elem:
            res_dic = {'content_type_model': 'shared_elements.note',
                       "element_pk": str(result["id"]),
                       'labbook_pos_y': lb_elem.position_y}
            result_array.append(res_dic)

    # search in files
    encoded_search_text = encode_umlauts_to_html(search_text)
    cleaned_f = func.regexp_replace(
        func.regexp_replace(
            models.File.description,
            r'data:([a-zA-Z0-9]+/[a-zA-Z0-9.+-]+);base64,[A-Za-z0-9+/=]+',
            '',
            'g'
        ),
        r'<[^>]+>',
        '',
        'g'
    )

    results = (
        db.query(models.File)
        .filter_by(deleted=False)
        .filter(
            or_(
                models.File.title.ilike(f"%{search_text}%"),
                func.lower(cleaned_f).ilike(f"%{encoded_search_text.lower()}%")
            )
        )
        .join(
            models.Labbookchildelement,
            and_(
                models.File.elem_id == models.Labbookchildelement.id,
                models.Labbookchildelement.labbook_id == labbook_pk
            )
        )
        .all()
    )

    for result in results:
        if result.elem_id:
            lb_elem = db.query(models.Labbookchildelement).get(result.elem_id)
            if lb_elem:
                res_dic = {'content_type_model': 'shared_elements.file',
                           'element_pk': str(result.id),
                           'labbook_pos_y': lb_elem.position_y}
                result_array.append(res_dic)

    search_res = typesense_search_all(
        typesense=typesense,
        collection="pictures",
        search_text=search_text,
        labbook_id=labbook_id,
    )

    for result in search_res:
        result = result["document"]
        lb_elem = db.query(models.Labbookchildelement).get(
            result["elem_id"])
        if lb_elem:
            res_dic = {
                "content_type_model": "pictures.picture",
                "element_pk": str(result["id"]),
                "labbook_pos_y": lb_elem.position_y,
            }
            result_array.append(res_dic)

    result_array.sort(key=lambda x: x["labbook_pos_y"])
    return result_array


def typesense_search_all(typesense, collection, search_text, labbook_id,
                         per_page=250):
    page = 1
    results = []

    while True:
        query = [{
            "collection": collection,
            "q": search_text,
            "filter_by": f"labbook_id:[{labbook_id}] && soft_delete:=false",
            "query_by": "subject,content",
            "fuzzy": True,
            "limit": per_page,
            "page": page,
        }]

        response = typesense.multi_search.perform({"searches": query}, {})
        hits = response["results"][0]["hits"]

        if not hits:
            break  # no more pages
        results.extend(hits)

        if len(hits) < per_page:
            break  # last page reached
        page += 1

    return results
