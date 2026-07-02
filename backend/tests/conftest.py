"""
Shared pytest fixtures.

Tests run against an in-memory SQLite database rather than the real
MS SQL Server instance — fast, no external dependency, no shared
state between tests. The app's `get_db` dependency is overridden so
endpoint tests exercise the real FastAPI app + routing + dependency
graph, just swapping out where the data lives.

A single module-level SQLite engine is shared across all sessions so
that code paths that create their own ``SessionLocal`` (e.g. Celery
tasks in ``app/tasks/ingestion.py``) see the same in-memory database
as the test fixture session.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import get_db
from app.main import app
from app.models import Base

# ------------------------------------------------------------------
# Single in-memory SQLite engine shared by ALL sessions in tests.
# This ensures that code paths which call SessionLocal() directly
# (e.g. Celery tasks) connect to the same database as the fixture.
# ------------------------------------------------------------------
_test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=_test_engine, autoflush=False, autocommit=False)


@pytest.fixture()
def db_session(monkeypatch):
    # Patch SessionLocal so that any code importing it (e.g. Celery
    # tasks in ingestion, classification, main) gets the test session
    # maker instead of the real one that points at MS SQL Server.
    import app.main as app_main
    import app.tasks.classification
    import app.tasks.ingestion

    monkeypatch.setattr(app.tasks.ingestion, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(app.tasks.classification, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(app_main, "SessionLocal", TestingSessionLocal)

    Base.metadata.create_all(_test_engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(_test_engine)


@pytest.fixture()
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass  # db_session fixture owns the lifecycle/cleanup

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
