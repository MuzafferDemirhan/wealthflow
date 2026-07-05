"""
Service layer tests for Plaid connect flows.

Mocks PlaidAdapter at the provider level and exercises connect_service
functions that orchestrate link-token creation and token exchange.
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from cryptography.fernet import Fernet

from app.models.bank_connection import BankConnection, BankProvider, ConnectionStatus
from app.models.user import User, UserRole
from app.services import connect_service
from app.services.providers.plaid import PlaidProviderError


@pytest.fixture(autouse=True)
def _set_encryption_key(monkeypatch):
    """Set a valid Fernet key for encryption tests."""
    key = Fernet.generate_key().decode()
    monkeypatch.setattr("app.core.config.settings.TOKEN_ENCRYPTION_KEY", key)


@pytest.fixture()
def user(db_session):
    u = User(
        id=uuid.uuid4(),
        email="plaid@example.com",
        hashed_password="x",
        full_name="Plaid User",
        role=UserRole.USER,
    )
    db_session.add(u)
    db_session.commit()
    return u


# ------------------------------------------------------------------
# create_plaid_link_token
# ------------------------------------------------------------------


@patch("app.services.connect_service._build_plaid_provider")
def test_create_plaid_link_token_returns_token(mock_build):
    mock_provider = MagicMock()
    mock_provider.create_link_token.return_value = "link-sandbox-abc"
    mock_build.return_value = mock_provider

    result = connect_service.create_plaid_link_token(user_id=uuid.uuid4())
    assert result == {"link_token": "link-sandbox-abc"}


@patch("app.services.connect_service._build_plaid_provider")
def test_create_plaid_link_token_provider_error_raises_connect_error(mock_build):
    mock_provider = MagicMock()
    mock_provider.create_link_token.side_effect = PlaidProviderError("API down")
    mock_build.return_value = mock_provider

    with pytest.raises(connect_service.ConnectError, match="Failed to create Plaid link token"):
        connect_service.create_plaid_link_token(user_id=uuid.uuid4())


# ------------------------------------------------------------------
# exchange_plaid_public_token
# ------------------------------------------------------------------


@patch("app.services.connect_service._build_plaid_provider")
@patch("app.services.connect_service._encrypt_token", return_value="encrypted-token")
def test_exchange_public_token_creates_connection_and_accounts(
    mock_encrypt, mock_build, db_session, user
):
    mock_provider = MagicMock()
    mock_provider.exchange_public_token.return_value = ("access-sandbox-xyz", "item-123")
    mock_provider.fetch_accounts.return_value = []
    mock_build.return_value = mock_provider

    result = connect_service.exchange_plaid_public_token(
        db_session,
        user_id=user.id,
        public_token="public-sandbox-abc",
        institution_id="inst_plaid_test",
        institution_name="Plaid Test Bank",
    )

    assert result["item_id"] == "item-123"
    assert result["institution_id"] == "inst_plaid_test"
    assert result["accounts_created"] == []

    # Verify connection was saved
    from sqlalchemy import select
    conn = db_session.scalar(
        select(BankConnection).where(
            BankConnection.user_id == user.id,
            BankConnection.provider == BankProvider.PLAID,
        )
    )
    assert conn is not None
    assert conn.status == ConnectionStatus.LINKED
    assert conn.external_reference == "encrypted-token"


@patch("app.services.connect_service._build_plaid_provider")
def test_exchange_public_token_stores_encrypted_token(mock_build, db_session, user):
    """Assert stored value != raw access_token (i.e. it's encrypted)."""
    mock_provider = MagicMock()
    mock_provider.exchange_public_token.return_value = ("access-sandbox-xyz", "item-123")
    mock_provider.fetch_accounts.return_value = []
    mock_build.return_value = mock_provider

    result = connect_service.exchange_plaid_public_token(
        db_session,
        user_id=user.id,
        public_token="public-sandbox-abc",
        institution_id="inst_test",
        institution_name="Test",
    )

    conn = db_session.get(BankConnection, result["id"])
    assert conn.external_reference != "access-sandbox-xyz"


@patch("app.services.connect_service._build_plaid_provider")
def test_exchange_public_token_provider_error_raises_connect_error(mock_build, db_session, user):
    mock_provider = MagicMock()
    mock_provider.exchange_public_token.side_effect = PlaidProviderError("exchange failed")
    mock_build.return_value = mock_provider

    with pytest.raises(connect_service.ConnectError, match="Plaid token exchange failed"):
        connect_service.exchange_plaid_public_token(
            db_session,
            user_id=user.id,
            public_token="bad-token",
            institution_id="inst_test",
            institution_name="Test",
        )
