"""
API integration tests for Plaid endpoints.

Uses the existing `client` fixture (FastAPI TestClient with SQLite).
PlaidAdapter is mocked to avoid real API calls.
"""

import uuid
from unittest.mock import patch

import jwt
import pytest
from cryptography.fernet import Fernet

from app.core.config import settings
from app.core.security import ALGORITHM
from app.models.user import User, UserRole


@pytest.fixture(autouse=True)
def _set_encryption_key(monkeypatch):
    """Set a valid Fernet key for encryption tests."""
    key = Fernet.generate_key().decode()
    monkeypatch.setattr("app.core.config.settings.TOKEN_ENCRYPTION_KEY", key)


@pytest.fixture()
def user(db_session):
    u = User(
        id=uuid.uuid4(),
        email="plaid-api@example.com",
        hashed_password="x",
        full_name="Plaid API User",
        role=UserRole.USER,
    )
    db_session.add(u)
    db_session.commit()
    return u


def auth_header(user_id: uuid.UUID) -> dict:
    token = jwt.encode(
        {"sub": str(user_id), "type": "access"},
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )
    return {"Authorization": f"Bearer {token}"}


# ------------------------------------------------------------------
# POST /connect/plaid/link-token
# ------------------------------------------------------------------


@patch("app.services.connect_service._build_plaid_provider")
def test_create_link_token_endpoint_requires_auth(mock_build, client):
    resp = client.post("/api/v1/connect/plaid/link-token", json={})
    assert resp.status_code == 401


@patch("app.services.connect_service._build_plaid_provider")
def test_create_link_token_endpoint_success(mock_build, client, user):
    mock_provider = mock_build.return_value
    mock_provider.create_link_token.return_value = "link-sandbox-abc"

    resp = client.post(
        "/api/v1/connect/plaid/link-token",
        json={},
        headers=auth_header(user.id),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["link_token"] == "link-sandbox-abc"


@patch("app.services.connect_service._build_plaid_provider")
def test_create_link_token_endpoint_provider_error_returns_502(mock_build, client, user):
    from app.services.providers.plaid import PlaidProviderError

    mock_provider = mock_build.return_value
    mock_provider.create_link_token.side_effect = PlaidProviderError("API error")

    resp = client.post(
        "/api/v1/connect/plaid/link-token",
        json={},
        headers=auth_header(user.id),
    )
    assert resp.status_code == 502


# ------------------------------------------------------------------
# POST /connect/plaid/exchange
# ------------------------------------------------------------------


@patch("app.services.connect_service._build_plaid_provider")
def test_exchange_endpoint_requires_auth(mock_build, client):
    resp = client.post(
        "/api/v1/connect/plaid/exchange",
        json={"public_token": "abc", "institution_id": "inst", "institution_name": "Test"},
    )
    assert resp.status_code == 401


@patch("app.services.connect_service._build_plaid_provider")
def test_exchange_endpoint_success_returns_201(mock_build, client, user):
    mock_provider = mock_build.return_value
    mock_provider.exchange_public_token.return_value = ("access-sandbox-xyz", "item-123")
    mock_provider.fetch_accounts.return_value = []

    resp = client.post(
        "/api/v1/connect/plaid/exchange",
        json={
            "public_token": "public-sandbox-abc",
            "institution_id": "inst_plaid_test",
            "institution_name": "Plaid Test Bank",
        },
        headers=auth_header(user.id),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["institution_id"] == "inst_plaid_test"
    assert data["item_id"] == "item-123"
    assert data["accounts_created"] == []


@patch("app.services.connect_service._build_plaid_provider")
def test_exchange_endpoint_provider_error_returns_502(mock_build, client, user):
    from app.services.providers.plaid import PlaidProviderError

    mock_provider = mock_build.return_value
    mock_provider.exchange_public_token.side_effect = PlaidProviderError("exchange failed")

    resp = client.post(
        "/api/v1/connect/plaid/exchange",
        json={
            "public_token": "bad",
            "institution_id": "inst",
            "institution_name": "Test",
        },
        headers=auth_header(user.id),
    )
    assert resp.status_code == 502
