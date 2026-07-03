"""
SQLAlchemy engine and session management.

Uses a synchronous engine (pyodbc) rather than the async driver
(aioodbc). The async MS SQL Server driver stack is still immature
(no native async pyodbc, aioodbc wraps blocking calls in a thread
pool anyway), so a sync engine run through FastAPI's threadpool via
plain `def` endpoints - or wrapped with `run_in_threadpool` - is the
more reliable choice for SQL Server. This can be revisited later if
a specific endpoint needs true async DB I/O.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

_url = make_url(settings.DATABASE_URL)

# QueuePool-specific options are invalid for backends that don't use
# QueuePool by default (e.g. SQLite's SingletonThreadPool, used in
# local tests). Only pass them when targeting a real server backend.
_engine_kwargs: dict = {"pool_pre_ping": True, "future": True}
if _url.get_backend_name() != "sqlite":
    _engine_kwargs.update(pool_size=10, max_overflow=20)

engine = create_engine(settings.DATABASE_URL, **_engine_kwargs)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    future=True,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a request-scoped DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
