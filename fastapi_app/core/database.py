import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from .config import settings


_db_url = settings.database_url
if not _db_url or _db_url.startswith("postgresql") is False:
    _db_url = os.getenv("DATABASE_URL", "sqlite:///./medaea_dev.db")

_connect_args = {"check_same_thread": False} if _db_url.startswith("sqlite") else {}

engine = create_engine(
    _db_url,
    connect_args=_connect_args,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from backend.fastapi_app.db import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
