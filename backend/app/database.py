"""DB engine + session. SQLite for dev; Postgres for prod (incl. serverless)."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import NullPool

from .config import settings

kwargs: dict = {"pool_pre_ping": True}
if settings.database_url.startswith("sqlite"):
    kwargs["connect_args"] = {"check_same_thread": False}
if settings.serverless:
    # Each function invocation is short-lived; don't hold a pool across them.
    kwargs["poolclass"] = NullPool
    kwargs.pop("pool_pre_ping", None)

engine = create_engine(settings.database_url, **kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
