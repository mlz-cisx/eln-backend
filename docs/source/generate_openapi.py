import os
import sys
from pathlib import Path

import yaml
from fastapi.openapi.utils import get_openapi

sys.path.append(os.path.abspath(Path(__file__).parent.parent.parent))
from joeseln_backend.main import app


def generate_openapi_yaml():
    openapi_schema = get_openapi(
        title="API",
        version="1.0.0",
        routes=app.routes,
    )
    with open(
        os.path.abspath(Path(__file__).parent / "_static/openapi.yaml"), "w"
    ) as f:
        yaml.dump(openapi_schema, f, sort_keys=False)


if __name__ == "__main__":
    generate_openapi_yaml()
