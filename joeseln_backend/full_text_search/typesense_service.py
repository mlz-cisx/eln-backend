from typing import Dict

from typesense import Client
from typesense.configuration import ConfigDict
from typesense.exceptions import ObjectNotFound, TypesenseClientError
from typesense.types.collection import CollectionCreateSchema

from joeseln_backend.conf.base_conf import (
    TYPESENSE_API_KEY,
    TYPESENSE_HOST,
    TYPESENSE_PORT,
    TYPESENSE_PROTOCOL,
)
from joeseln_backend.full_text_search.html_stripper import strip_html_and_binary
from joeseln_backend.models.models import File, Note, Picture
from joeseln_backend.mylogging.root_logger import logger


class TypesenseService:
    def __init__(
        self, COLLECTIONS: Dict[str, CollectionCreateSchema], CONFIG: ConfigDict
    ) -> None:
        self.client = None
        self.collections = COLLECTIONS
        self.config = CONFIG

    def connect_typesense_client(self) -> None:
        self.client = Client(self.config)

    def create_collection(self) -> None:
        if self.client is None:
            raise ConnectionError("typesense disconnected")
        for schema in self.collections.keys():
            try:
                self.client.collections[schema].retrieve()
            except ObjectNotFound:
                self.client.collections.create(self.collections[schema])

    def get_client(self) -> Client:
        if self.client is None:
            raise ConnectionError("typesense disconnected")
        return self.client


collections: Dict[str, CollectionCreateSchema] = {
    "notes": {
        "name": "notes",
        "fields": [
            {"name": "id", "type": "string"},
            {"name": "elem_id", "type": "string"},
            {
                "name": "subject",
                "type": "string",
                "index": True,
                "infix": True,
                "facet": True,
            },
            {
                "name": "content",
                "type": "string",
                "index": True,
                "infix": True,
                "facet": True,
            },
            {"name": "last_modified_at", "type": "int64"},
            {"name": "labbook_id", "type": "string"},
            {"name": "soft_delete", "type": "bool"},
        ],
        "default_sorting_field": "last_modified_at",
    },
    "pictures": {
        "name": "pictures",
        "fields": [
            {"name": "id", "type": "string"},
            {"name": "elem_id", "type": "string"},
            {
                "name": "subject",
                "type": "string",
                "index": True,
                "infix": True,
                "facet": True,
            },
            {
                "name": "content",
                "type": "string",
                "index": True,
                "infix": True,
                "facet": True,
            },
            {"name": "last_modified_at", "type": "int64"},
            {"name": "labbook_id", "type": "string"},
            {"name": "soft_delete", "type": "bool"},
        ],
        "default_sorting_field": "last_modified_at",
    },
}

collections["files"] = {**collections["notes"], "name": "files"}

config: ConfigDict = {
    "api_key": TYPESENSE_API_KEY,
    "nodes": [
        {
            "host": TYPESENSE_HOST,
            "port": TYPESENSE_PORT,
            "protocol": TYPESENSE_PROTOCOL,
        }
    ],
    "connection_timeout_seconds": 2,
}


typesense_client = TypesenseService(collections, config)


def get_typesense_client():
    return typesense_client.get_client()


def update_delete_status_typesense(
    elem: Note | Picture | File, deleted: bool, typesense: Client
):
    try:
        table = {Note: "notes", Picture: "pictures", File: "files"}[type(elem)]
        typesense.collections[table].documents[str(elem.id)].update(
            {"soft_delete": deleted}
        )
    except TypesenseClientError as e:
        logger.error(e)


def update_file_typesense(file, lb_elem, typesense=None):
    try:
        if typesense is None:
            typesense = get_typesense_client()
        typesense.collections["files"].documents.upsert({
            "id": str(file.id),
            "elem_id": str(lb_elem.id),
            "subject": file.title or "",
            "content": strip_html_and_binary(file.description or ""),
            "last_modified_at": int(file.last_modified_at.timestamp()),
            "labbook_id": str(lb_elem.labbook_id),
            "soft_delete": bool(file.deleted or lb_elem.deleted),
        })
    except TypesenseClientError as e:
        logger.error(e)
