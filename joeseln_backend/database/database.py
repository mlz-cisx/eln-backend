from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from joeseln_backend.conf.base_conf import (
    DB_ADDR,
    DB_PASSWORD,
    DB_PORT,
    DB_TABLE,
    DB_USER,
)

_user = DB_USER
_password = DB_PASSWORD
_db = DB_TABLE
_port = DB_PORT
_addr = DB_ADDR

SQLALCHEMY_DATABASE_URL = f"postgresql://{_user}:{_password}@{_addr}:{_port}/{_db}"

engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_size=20, max_overflow=50)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
