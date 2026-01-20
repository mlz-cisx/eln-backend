from typing import Dict

import typesense
from typesense.client import Client
from typesense.configuration import ConfigDict
from typesense.exceptions import ObjectNotFound
from typesense.types.collection import CollectionCreateSchema

from joeseln_backend.conf.base_conf import (
    TYPESENSE_API_KEY,
    TYPESENSE_HOST,
    TYPESENSE_PORT,
    TYPESENSE_PROTOCOL,
)


class TypesenseService:
    def __init__(
        self, COLLECTIONS: Dict[str, CollectionCreateSchema], CONFIG: ConfigDict
    ) -> None:
        self.client = None
        self.collections = COLLECTIONS
        self.config = CONFIG

    def connect_typesense_client(self) -> None:
        self.client = typesense.client.Client(self.config)

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

config: ConfigDict = {
    "api_key": TYPESENSE_API_KEY,
    "nodes": [
        {
            "host": TYPESENSE_HOST,
            "port": TYPESENSE_PORT,
            "protocol": TYPESENSE_PROTOCOL,
        }
    ],
    "timeout_seconds": 2,
}


typesense_client = TypesenseService(collections, config)


def get_typesense_client():
    return typesense_client.get_client()
