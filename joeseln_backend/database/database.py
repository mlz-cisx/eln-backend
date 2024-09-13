from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from joeseln_backend.conf.base_conf import DB_USER, DB_PASSWORD, DB_TABLE, \
    DB_PORT

_user = DB_USER
_password = DB_PASSWORD
_db = DB_TABLE
_port = DB_PORT

SQLALCHEMY_DATABASE_URL = f"postgresql://{_user}:{_password}@localhost:{_port}/{_db}"

engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_size=20, max_overflow=50)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
