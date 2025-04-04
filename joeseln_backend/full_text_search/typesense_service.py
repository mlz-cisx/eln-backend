import typesense
from typesense.exceptions import ObjectNotFound
from joeseln_backend.conf.base_conf import (
    TYPESENSE_API_KEY,
    TYPESENSE_HOST,
    TYPESENSE_PORT,
    TYPESENSE_PROTOCOL,
)
def create_typesense_client():
    client = typesense.client.Client(
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
    return client

def create_typesense_collection(client):
    COLLECTION_NAME = "notes"
    COLLECTION_SCHEMA = {
        "name": COLLECTION_NAME,
        "fields": [
            {"name": "id", "type": "string"},
            {"name": "elem_id", "type": "string"},
            {"name": "subject", "type": "string", "tokenizer": "word", "index": True, "infix": True, "facet": True},
            {"name": "content", "type": "string", "tokenizer": "word", "index": True, "infix": True, "facet": True},
            {"name": "last_modified_at", "type": "int64"},
            {"name": "labbook_id", "type": "string"},
            {"name": "soft_delete", "type": "bool"},
        ],
        "default_sorting_field": "last_modified_at",
    }
    try:
        client.collections[COLLECTION_NAME].retrieve()
        return
    except ObjectNotFound:
        client.collections.create(COLLECTION_SCHEMA)
