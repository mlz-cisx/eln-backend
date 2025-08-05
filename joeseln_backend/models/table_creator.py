from joeseln_backend.database.database import engine
from joeseln_backend.models import models


def table_creator():
    models.Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    table_creator()
