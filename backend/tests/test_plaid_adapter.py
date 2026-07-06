"""
Unit tests for PlaidAdapter.

The Plaid Python SDK is mocked to avoid requiring API credentials.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import plaid
import pytest

from app.services.providers.plaid import PlaidAdapter, PlaidProviderError

# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture()
def adapter():
    with patch("app.services.providers.plaid._build_plaid_client", return_value=MagicMock()):
        yield PlaidAdapter(
            client_id="test_client_id",
            secret="test_secret",
            env="sandbox",
        )


# ------------------------------------------------------------------
# Constructor
# ------------------------------------------------------------------


def test_missing_credentials_raises():
    with pytest.raises(PlaidProviderError, match="Plaid is not configured"):
        PlaidAdapter(client_id="", secret="", env="sandbox")

    with pytest.raises(PlaidProviderError, match="Plaid is not configured"):
        PlaidAdapter(client_id="x", secret="", env="sandbox")


# ------------------------------------------------------------------
# Link token
# ------------------------------------------------------------------


@patch("app.services.providers.plaid.plaid_api.PlaidApi")
def test_create_link_token_success(MockPlaidApi, adapter):
    mock_client = MagicMock()
    mock_client.link_token_create.return_value = {"link_token": "link-sandbox-abc123"}
    adapter._client = mock_client

    token = adapter.create_link_token(user_id="user-uuid")
    assert token == "link-sandbox-abc123"
    mock_client.link_token_create.assert_called_once()


@patch("app.services.providers.plaid.plaid_api.PlaidApi")
def test_create_link_token_api_error_raises(MockPlaidApi, adapter):
    mock_client = MagicMock()
    mock_client.link_token_create.side_effect = plaid.ApiException(
        http_resp=MagicMock(status=400, data=b'{"error":"bad request"}')
    )
    adapter._client = mock_client

    with pytest.raises(PlaidProviderError, match="Failed to create link token"):
        adapter.create_link_token(user_id="user-uuid")


# ------------------------------------------------------------------
# Token exchange
# ------------------------------------------------------------------


@patch("app.services.providers.plaid.plaid_api.PlaidApi")
def test_exchange_public_token_success(MockPlaidApi, adapter):
    mock_client = MagicMock()
    mock_client.item_public_token_exchange.return_value = {
        "access_token": "access-sandbox-xyz",
        "item_id": "item-sandbox-999",
    }
    adapter._client = mock_client

    access_token, item_id = adapter.exchange_public_token("public-sandbox-123")
    assert access_token == "access-sandbox-xyz"
    assert item_id == "item-sandbox-999"


@patch("app.services.providers.plaid.plaid_api.PlaidApi")
def test_exchange_public_token_api_error_raises(MockPlaidApi, adapter):
    mock_client = MagicMock()
    mock_client.item_public_token_exchange.side_effect = plaid.ApiException(
        http_resp=MagicMock(status=400, data=b'{"error":"invalid token"}')
    )
    adapter._client = mock_client

    with pytest.raises(PlaidProviderError, match="Token exchange failed"):
        adapter.exchange_public_token("bad-token")


# ------------------------------------------------------------------
# Fetch accounts
# ------------------------------------------------------------------


@patch("app.services.providers.plaid.plaid_api.PlaidApi")
def test_fetch_accounts_success(MockPlaidApi, adapter):
    mock_client = MagicMock()
    mock_client.accounts_get.return_value = {
        "accounts": [
            {
                "account_id": "acc1",
                "name": "Checking Account",
                "type": "depository",
                "subtype": "checking",
                "balances": {
                    "current": 1500.50,
                    "iso_currency_code": "USD",
                },
            },
            {
                "account_id": "acc2",
                "name": "Credit Card",
                "type": "credit",
                "subtype": "credit card",
                "balances": {
                    "current": -450.00,
                    "iso_currency_code": "USD",
                },
            },
        ]
    }
    adapter._client = mock_client

    accounts = adapter.fetch_accounts("access-token")
    assert len(accounts) == 2
    assert accounts[0].external_account_id == "acc1"
    assert accounts[0].account_type == "checking"
    assert accounts[0].current_balance == Decimal("1500.50")
    assert accounts[1].account_type == "credit_card"
    assert accounts[1].current_balance == Decimal("-450.00")


@patch("app.services.providers.plaid.plaid_api.PlaidApi")
def test_fetch_accounts_maps_unknown_type_to_other(MockPlaidApi, adapter):
    mock_client = MagicMock()
    mock_client.accounts_get.return_value = {
        "accounts": [
            {
                "account_id": "acc3",
                "name": "Unknown",
                "type": "brokerage",
                "subtype": "",
                "balances": {"current": 100, "iso_currency_code": "USD"},
            },
        ]
    }
    adapter._client = mock_client

    accounts = adapter.fetch_accounts("access-token")
    assert accounts[0].account_type == "other"


# ------------------------------------------------------------------
# Parse transaction
# ------------------------------------------------------------------


def test_parse_plaid_transaction_flips_sign():
    """Plaid positive = debit, WealthFlow negative = expense."""
    raw = {
        "transaction_id": "txn1",
        "amount": 50.00,
        "iso_currency_code": "USD",
        "date": "2024-03-15",
        "name": "Uber Ride",
        "merchant_name": "Uber",
        "pending": False,
    }
    parsed = PlaidAdapter._parse_plaid_transaction(raw)
    assert parsed is not None
    assert parsed.amount == Decimal("-50.00")
    assert parsed.external_id == "txn1"
    assert parsed.description == "Uber Ride"
    assert parsed.counterparty_name == "Uber"
    assert parsed.status == "booked"


def test_parse_plaid_transaction_pending_status():
    raw = {
        "transaction_id": "txn2",
        "amount": 25.00,
        "iso_currency_code": "USD",
        "date": "2024-03-16",
        "name": "Coffee",
        "pending": True,
    }
    parsed = PlaidAdapter._parse_plaid_transaction(raw)
    assert parsed is not None
    assert parsed.status == "pending"


def test_parse_plaid_transaction_missing_date_returns_none():
    raw = {
        "transaction_id": "txn3",
        "amount": 10.00,
        "iso_currency_code": "USD",
        "date": None,
        "name": "Test",
    }
    assert PlaidAdapter._parse_plaid_transaction(raw) is None


def test_parse_plaid_transaction_missing_amount_returns_none():
    raw = {
        "transaction_id": "txn4",
        "amount": None,
        "iso_currency_code": "USD",
        "date": "2024-03-17",
        "name": "Test",
    }
    assert PlaidAdapter._parse_plaid_transaction(raw) is None


# ------------------------------------------------------------------
# Requisition methods
# ------------------------------------------------------------------


def test_authenticate_returns_placeholder(adapter):
    assert adapter.authenticate() == "plaid-client-credentials"


def test_create_requisition_returns_link_token(adapter):
    with patch.object(adapter, "create_link_token", return_value="link-token-abc"):
        result = adapter.create_requisition(
            institution_id="inst_1",
            redirect_uri="https://example.com/callback",
            reference="user-uuid",
        )
    assert result["link_token"] == "link-token-abc"
    assert result["url"] is None
    assert result["authorization_id"] == "user-uuid"


def test_get_requisition_returns_authorized(adapter):
    result = adapter.get_requisition("any-id")
    assert result["status"] == "AUTHORIZED"
