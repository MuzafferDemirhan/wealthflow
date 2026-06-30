"""
Shared pytest fixtures.

Tests run against an in-memory SQLite database rather than the real
MS SQL Server instance — fast, no external dependency, no shared
state between tests. The app's `get_db` dependency is overridden so
endpoint tests exercise the real FastAPI app + routing + dependency
graph, just swapping out where the data lives.

Note: `app.db.session.engine` (the "real" engine pointing at
`settings.DATABASE_URL`, i.e. MS SQL Server) is still created at
import time, but since SQLAlchemy engines are lazy, this never
actually opens a connection during tests.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import get_db
from app.main import app
from app.models import Base


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


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
