import typesense
from typesense.exceptions import ObjectNotFound
from joeseln_backend.conf.base_conf import (
    TYPESENSE_API_KEY,
    TYPESENSE_HOST,
    TYPESENSE_PORT,
    TYPESENSE_PROTOCOL,
)


class TypesenseService:
    COLLECTION_NAME = "notes"
    COLLECTION_SCHEMA = {
        "name": COLLECTION_NAME,
        "fields": [
            {"name": "id", "type": "string"},
            {"name": "elem_id", "type": "string"},
            {
                "name": "subject",
                "type": "string",
                "tokenizer": "word",
                "index": True,
                "infix": True,
                "facet": True,
            },
            {
                "name": "content",
                "type": "string",
                "tokenizer": "word",
                "index": True,
                "infix": True,
                "facet": True,
            },
            {"name": "last_modified_at", "type": "int64"},
            {"name": "labbook_id", "type": "string"},
            {"name": "soft_delete", "type": "bool"},
        ],
        "default_sorting_field": "last_modified_at",
    }

    def __init__(self) -> None:
        self.client = None

    def connect_typesense_client(self):
        self.client = typesense.client.Client(
            {
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
        )

    def create_collection(self):
        if self.client is not None:
            try:
                self.client.collections[self.COLLECTION_NAME].retrieve()
            except ObjectNotFound:
                self.client.collections.create(self.COLLECTION_SCHEMA)

    def get_client(self):
        return self.client


typesense_client = TypesenseService()


def get_typesense_client():
    return typesense_client.get_client()
