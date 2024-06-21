from joeseln_backend.models import models
from joeseln_backend.database.database import engine


def table_creator():
    models.Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    table_creator()
