from typing import Literal, Optional

OrderingParam = Literal[
    "pk",
    "-pk",
    "subject",
    "-subject",
    "title",
    "-title",
    "created_at",
    "-created_at",
    "created_by",
    "-created_by",
    "last_modified_at",
    "-last_modified_at",
    "last_modified_by",
    "-last_modified_by",
    "name",
    "-name",
    "file_size",
    "-file_size",
    "groupname",
    "-groupname",
    "username",
    "-username",
    "first_name",
    "-first_name",
    "last_name",
    "-last_name",
    "email",
    "-email",
    "oidc_user",
    "-oidc_user",
    "connected",
    "-connected",
]


def get_order_params(ordering: Optional[OrderingParam]) -> str:
    match ordering:
        # defaults pk are mapped to created_at field
        case 'pk':
            return 'created_at asc'
        case '-pk':
            return 'created_at desc'
        case 'subject':
            return 'subject asc'
        case '-subject':
            return 'subject desc'
        case 'title':
            return 'title asc'
        case '-title':
            return 'title desc'
        case 'created_at':
            return 'created_at asc'
        case '-created_at':
            return 'created_at desc'
        case 'created_by':
            return 'created_by_id asc'
        case '-created_by':
            return 'created_by_id desc'
        case 'last_modified_at':
            return 'last_modified_at asc'
        case '-last_modified_at':
            return 'last_modified_at desc'
        case 'last_modified_by':
            return 'last_modified_by_id asc'
        case '-last_modified_by':
            return 'last_modified_by_id desc'
        case 'name':
            return 'name asc'
        case '-name':
            return 'name desc'
        case 'file_size':
            return 'file_size asc'
        case '-file_size':
            return 'file_size desc'
        case 'groupname':
            return 'groupname asc'
        case '-groupname':
            return 'groupname desc'
        case 'username':
            return 'username asc'
        case '-username':
            return 'username desc'
        case 'first_name':
            return 'first_name asc'
        case '-first_name':
            return 'first_name desc'
        case 'last_name':
            return 'last_name asc'
        case '-last_name':
            return 'last_name desc'
        case 'email':
            return 'email asc'
        case '-email':
            return 'email desc'
        case 'oidc_user':
            return 'oidc_user asc'
        case '-oidc_user':
            return 'oidc_user desc'
        case 'connected':
            return 'connected asc'
        case '-connected':
            return 'connected desc'
        case None:
            return 'created_at desc'
        case _:
            return 'created_at desc'
