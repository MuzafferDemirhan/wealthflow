import json
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional
from unittest.mock import ANY

import httpx
import pytest

from app.services.providers.base import ProviderAccount, ProviderTransaction
from app.services.providers.nordigen import (
    NordigenAdapter,
    ProviderError,
    _map_account_type,
    _parse_amount,
    _parse_date,
    _parse_datetime,
)

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

SECRET_ID = "test-secret-id"
SECRET_KEY = "test-secret-key"

TOKEN_RESPONSE = {
    "access": "access-token-123",
    "access_expires": 86400,
    "refresh": "refresh-token-456",
    "refresh_expires": 2592000,
}

INSTITUTION_ID = "SANDBOXFINANCE_SFIN0000"
REQUISITION_ID = "req-uuid-123"
ACCOUNT_UUID = "acc-uuid-abc"
REDIRECT_URI = "http://localhost:3000/callback"
REFERENCE = "ref-001"


def _mock_handler(register: dict) -> httpx.MockTransport:
    """Build a MockTransport that dispatches based on a (method, url) -> response dict."""

    def handler(request: httpx.Request) -> httpx.Response:
        key = (request.method, str(request.url).split("?")[0])
        for (method, url), response in register.items():
            if request.method == method and str(request.url).startswith(url):
                status = response.get("status", 200)
                body = response.get("body", {})
                return httpx.Response(status, json=body)
        return httpx.Response(404, json={"error": f"No mock for {key}"})

    return httpx.MockTransport(handler)


def _adapter(register: dict) -> NordigenAdapter:
    transport = _mock_handler(register)
    client = httpx.Client(transport=transport)
    return NordigenAdapter(
        secret_id=SECRET_ID,
        secret_key=SECRET_KEY,
        client=client,
    )


# ------------------------------------------------------------------
# Unit: helper functions
# ------------------------------------------------------------------


class TestMapAccountType:
    def test_known_types(self):
        assert _map_account_type("CACC") == "checking"
        assert _map_account_type("SVGS") == "savings"
        assert _map_account_type("CARD") == "credit_card"
        assert _map_account_type("LOAN") == "loan"
        assert _map_account_type("MGLD") == "investment"

    def test_unknown_type_falls_back(self):
        assert _map_account_type("OTHR") == "other"
        assert _map_account_type("") == "other"
        assert _map_account_type(None) == "other"

    def test_case_sensitivity(self):
        assert _map_account_type("cacc") == "other"


class TestParseDate:
    def test_full_datetime_string(self):
        assert _parse_date("2026-06-15T10:30:00Z") == date(2026, 6, 15)

    def test_date_only_string(self):
        assert _parse_date("2026-06-15") == date(2026, 6, 15)

    def test_none_returns_none(self):
        assert _parse_date(None) is None

    def test_empty_string_returns_none(self):
        assert _parse_date("") is None


class TestParseDatetime:
    def test_iso_datetime(self):
        dt = _parse_datetime("2026-06-15T10:30:00+00:00")
        assert dt is not None
        assert dt.year == 2026 and dt.month == 6 and dt.day == 15

    def test_date_only(self):
        dt = _parse_datetime("2026-06-15")
        assert dt is not None
        assert dt.year == 2026 and dt.month == 6 and dt.day == 15

    def test_none_returns_none(self):
        assert _parse_datetime(None) is None


class TestParseAmount:
    def test_string_amount(self):
        assert _parse_amount({"amount": "123.45", "currency": "EUR"}) == Decimal("123.45")

    def test_negative_amount(self):
        assert _parse_amount({"amount": "-50.00", "currency": "EUR"}) == Decimal("-50.00")

    def test_zero_amount(self):
        assert _parse_amount({"amount": "0", "currency": "EUR"}) == Decimal("0")

    def test_missing_amount_defaults_to_zero(self):
        assert _parse_amount({"currency": "EUR"}) == Decimal("0")


# ------------------------------------------------------------------
# Adapter: authentication
# ------------------------------------------------------------------


class TestAuthenticate:
    def test_successful_token_obtain(self):
        adapter = _adapter({
            ("POST", f"{NordigenAdapter.BASE_URL}/token/new/"): {
                "body": TOKEN_RESPONSE,
            },
        })
        token = adapter.authenticate()
        assert token == "access-token-123"

    def test_token_request_failure(self):
        adapter = _adapter({
            ("POST", f"{NordigenAdapter.BASE_URL}/token/new/"): {
                "status": 401,
                "body": {"error": "Invalid credentials"},
            },
        })
        with pytest.raises(ProviderError, match="Token request failed"):
            adapter.authenticate()

    def test_ensure_token_refreshes_when_expired(self):
        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "POST" and "token/new" in str(request.url):
                return httpx.Response(200, json=TOKEN_RESPONSE)
            if request.method == "POST" and "token/refresh" in str(request.url):
                return httpx.Response(200, json={
                    "access": "refreshed-token-789",
                    "access_expires": 86400,
                    "refresh": "new-refresh-token",
                    "refresh_expires": 2592000,
                })
            if request.method == "GET" and "requisitions" in str(request.url):
                return httpx.Response(200, json={"id": REQUISITION_ID, "accounts": []})
            return httpx.Response(404)

        client = httpx.Client(transport=httpx.MockTransport(handler))
        adapter = NordigenAdapter(
            secret_id=SECRET_ID,
            secret_key=SECRET_KEY,
            client=client,
        )
        adapter._access_token = "old-token"
        adapter._refresh_token = "old-refresh"
        adapter._token_expires_at = 0  # expired

        adapter.get_requisition(REQUISITION_ID)
        assert adapter._access_token == "refreshed-token-789"


# ------------------------------------------------------------------
# Adapter: fetch_accounts
# ------------------------------------------------------------------


class TestFetchAccounts:
    REQUISITION_RESPONSE = {
        "id": REQUISITION_ID,
        "status": "LN",
        "accounts": [ACCOUNT_UUID],
        "institution_id": INSTITUTION_ID,
    }
    DETAILS_RESPONSE = {
        "account": {
            "iban": "PL60102010260000000000000000",
            "currency": "PLN",
            "ownerName": "Jan Kowalski",
            "name": "Personal Account",
            "cashAccountType": "CACC",
        }
    }
    BALANCES_RESPONSE = {
        "balances": [
            {
                "balanceAmount": {"amount": "15000.50", "currency": "PLN"},
                "balanceType": "interimAvailable",
                "referenceDate": "2026-07-01",
            }
        ]
    }

    def test_fetch_accounts_success(self):
        adapter = _adapter({
            ("POST", f"{NordigenAdapter.BASE_URL}/token/new/"): {"body": TOKEN_RESPONSE},
            ("GET", f"{NordigenAdapter.BASE_URL}/requisitions/{REQUISITION_ID}/"): {
                "body": self.REQUISITION_RESPONSE,
            },
            ("GET", f"{NordigenAdapter.BASE_URL}/accounts/{ACCOUNT_UUID}/details/"): {
                "body": self.DETAILS_RESPONSE,
            },
            ("GET", f"{NordigenAdapter.BASE_URL}/accounts/{ACCOUNT_UUID}/balances/"): {
                "body": self.BALANCES_RESPONSE,
            },
        })
        accounts = adapter.fetch_accounts(REQUISITION_ID)

        assert len(accounts) == 1
        acc = accounts[0]
        assert acc.external_account_id == ACCOUNT_UUID
        assert acc.iban == "PL60102010260000000000000000"
        assert acc.currency == "PLN"
        assert acc.display_name == "Personal Account"
        assert acc.account_type == "checking"
        assert acc.current_balance == Decimal("15000.50")
        assert acc.balance_as_of is not None

    def test_fetch_accounts_empty(self):
        adapter = _adapter({
            ("POST", f"{NordigenAdapter.BASE_URL}/token/new/"): {"body": TOKEN_RESPONSE},
            ("GET", f"{NordigenAdapter.BASE_URL}/requisitions/{REQUISITION_ID}/"): {
                "body": {**self.REQUISITION_RESPONSE, "accounts": []},
            },
        })
        accounts = adapter.fetch_accounts(REQUISITION_ID)
        assert accounts == []

    def test_fetch_accounts_unknown_type_falls_back(self):
        details = dict(self.DETAILS_RESPONSE)
        details["account"]["cashAccountType"] = "OTHR"
        adapter = _adapter({
            ("POST", f"{NordigenAdapter.BASE_URL}/token/new/"): {"body": TOKEN_RESPONSE},
            ("GET", f"{NordigenAdapter.BASE_URL}/requisitions/{REQUISITION_ID}/"): {
                "body": self.REQUISITION_RESPONSE,
            },
            ("GET", f"{NordigenAdapter.BASE_URL}/accounts/{ACCOUNT_UUID}/details/"): {
                "body": details,
            },
            ("GET", f"{NordigenAdapter.BASE_URL}/accounts/{ACCOUNT_UUID}/balances/"): {
                "body": self.BALANCES_RESPONSE,
            },
        })
        accounts = adapter.fetch_accounts(REQUISITION_ID)
        assert accounts[0].account_type == "other"


# ------------------------------------------------------------------
# Adapter: fetch_transactions
# ------------------------------------------------------------------


class TestFetchTransactions:
    TRANSACTIONS_RESPONSE = {
        "transactions": {
            "booked": [
                {
                    "transactionId": "txn-001",
                    "bookingDate": "2026-06-15",
                    "valueDate": "2026-06-15",
                    "transactionAmount": {"amount": "-45.99", "currency": "PLN"},
                    "creditorName": "Supermarket ABC",
                    "remittanceInformationUnstructured": "Groceries",
                    "bankTransactionCode": "PMNT",
                },
                {
                    "bookingDate": "2026-06-14",
                    "transactionAmount": {"amount": "5000.00", "currency": "PLN"},
                    "creditorName": "Employer Co",
                    "remittanceInformationUnstructured": "Salary",
                },
            ],
            "pending": [
                {
                    "transactionId": "txn-003",
                    "bookingDate": "2026-06-16",
                    "transactionAmount": {"amount": "-12.50", "currency": "PLN"},
                    "debtorName": "Coffee Shop",
                    "pending": True,
                }
            ],
        }
    }

    def test_fetch_transactions_success(self):
        adapter = _adapter({
            ("POST", f"{NordigenAdapter.BASE_URL}/token/new/"): {"body": TOKEN_RESPONSE},
            ("GET", f"{NordigenAdapter.BASE_URL}/accounts/{ACCOUNT_UUID}/transactions/"): {
                "body": self.TRANSACTIONS_RESPONSE,
            },
        })
        txns = adapter.fetch_transactions(ACCOUNT_UUID, since=date(2026, 6, 1))

        assert len(txns) == 3

        t1 = txns[0]
        assert t1.external_id == "txn-001"
        assert t1.amount == Decimal("-45.99")
        assert t1.currency == "PLN"
        assert t1.booking_date == date(2026, 6, 15)
        assert t1.description == "Groceries"
        assert t1.counterparty_name == "Supermarket ABC"
        assert t1.status == "booked"

        t2 = txns[1]
        assert t2.external_id is None
        assert t2.amount == Decimal("5000.00")

        t3 = txns[2]
        assert t3.status == "pending"
        assert t3.counterparty_name == "Coffee Shop"

    def test_fetch_transactions_uses_date_range(self):
        requests = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            if request.method == "POST" and "token/new" in str(request.url):
                return httpx.Response(200, json=TOKEN_RESPONSE)
            if request.method == "GET" and "transactions" in str(request.url):
                return httpx.Response(200, json=self.TRANSACTIONS_RESPONSE)
            return httpx.Response(404)

        client = httpx.Client(transport=httpx.MockTransport(handler))
        adapter = NordigenAdapter(SECRET_ID, SECRET_KEY, client=client)
        adapter.fetch_transactions(ACCOUNT_UUID, since=date(2026, 6, 1))

        txn_req = next(r for r in requests if "transactions" in str(r.url))
        assert "date_from=2026-06-01" in str(txn_req.url)
        assert "date_to=" in str(txn_req.url)

    def test_fetch_transactions_empty(self):
        adapter = _adapter({
            ("POST", f"{NordigenAdapter.BASE_URL}/token/new/"): {"body": TOKEN_RESPONSE},
            ("GET", f"{NordigenAdapter.BASE_URL}/accounts/{ACCOUNT_UUID}/transactions/"): {
                "body": {"transactions": {"booked": [], "pending": []}},
            },
        })
        txns = adapter.fetch_transactions(ACCOUNT_UUID, since=date(2026, 1, 1))
        assert txns == []


# ------------------------------------------------------------------
# Adapter: fetch_balances
# ------------------------------------------------------------------


class TestFetchBalances:
    def test_prefers_interim_available(self):
        adapter = _adapter({
            ("POST", f"{NordigenAdapter.BASE_URL}/token/new/"): {"body": TOKEN_RESPONSE},
            ("GET", f"{NordigenAdapter.BASE_URL}/accounts/{ACCOUNT_UUID}/balances/"): {
                "body": {
                    "balances": [
                        {
                            "balanceAmount": {"amount": "500.00", "currency": "PLN"},
                            "balanceType": "interimAvailable",
                            "referenceDate": "2026-07-01",
                        },
                        {
                            "balanceAmount": {"amount": "600.00", "currency": "PLN"},
                            "balanceType": "closingBooked",
                            "referenceDate": "2026-06-30",
                        },
                    ]
                },
            },
        })
        bal, as_of = adapter.fetch_balances(ACCOUNT_UUID)
        assert bal == Decimal("500.00")
        assert as_of is not None

    def test_fallback_to_first_balance(self):
        adapter = _adapter({
            ("POST", f"{NordigenAdapter.BASE_URL}/token/new/"): {"body": TOKEN_RESPONSE},
            ("GET", f"{NordigenAdapter.BASE_URL}/accounts/{ACCOUNT_UUID}/balances/"): {
                "body": {
                    "balances": [
                        {
                            "balanceAmount": {"amount": "1000.00", "currency": "PLN"},
                            "balanceType": "openingBooked",
                            "referenceDate": "2026-01-01",
                        }
                    ]
                },
            },
        })
        bal, as_of = adapter.fetch_balances(ACCOUNT_UUID)
        assert bal == Decimal("1000.00")

    def test_no_balances_returns_zero(self):
        adapter = _adapter({
            ("POST", f"{NordigenAdapter.BASE_URL}/token/new/"): {"body": TOKEN_RESPONSE},
            ("GET", f"{NordigenAdapter.BASE_URL}/accounts/{ACCOUNT_UUID}/balances/"): {
                "body": {"balances": []},
            },
        })
        bal, as_of = adapter.fetch_balances(ACCOUNT_UUID)
        assert bal == Decimal("0")
        assert as_of is None


# ------------------------------------------------------------------
# Adapter: requisition CRUD
# ------------------------------------------------------------------


class TestCreateRequisition:
    RESPONSE = {
        "id": REQUISITION_ID,
        "status": "CR",
        "link": "https://bankaccountdata.gocardless.com/..."
                "?ref=123",
        "institution_id": INSTITUTION_ID,
        "reference": REFERENCE,
        "accounts": [],
    }

    def test_creates_and_returns_requisition(self):
        adapter = _adapter({
            ("POST", f"{NordigenAdapter.BASE_URL}/token/new/"): {"body": TOKEN_RESPONSE},
            ("POST", f"{NordigenAdapter.BASE_URL}/requisitions/"): {"body": self.RESPONSE},
        })
        result = adapter.create_requisition(INSTITUTION_ID, REDIRECT_URI, REFERENCE)
        assert result["id"] == REQUISITION_ID
        assert result["status"] == "CR"
        assert "link" in result


class TestGetRequisition:
    RESPONSE = {
        "id": REQUISITION_ID,
        "status": "LN",
        "accounts": [ACCOUNT_UUID],
        "institution_id": INSTITUTION_ID,
    }

    def test_returns_requisition(self):
        adapter = _adapter({
            ("POST", f"{NordigenAdapter.BASE_URL}/token/new/"): {"body": TOKEN_RESPONSE},
            ("GET", f"{NordigenAdapter.BASE_URL}/requisitions/{REQUISITION_ID}/"): {
                "body": self.RESPONSE,
            },
        })
        result = adapter.get_requisition(REQUISITION_ID)
        assert result["id"] == REQUISITION_ID
        assert result["status"] == "LN"
        assert ACCOUNT_UUID in result["accounts"]


# ------------------------------------------------------------------
# Adapter: error handling
# ------------------------------------------------------------------


class TestErrorHandling:
    def test_http_404_raises_provider_error(self):
        adapter = _adapter({
            ("POST", f"{NordigenAdapter.BASE_URL}/token/new/"): {"body": TOKEN_RESPONSE},
            ("GET", f"{NordigenAdapter.BASE_URL}/requisitions/nonexistent/"): {
                "status": 404,
                "body": {"error": "Not found"},
            },
        })
        with pytest.raises(ProviderError, match="GET.*/requisitions/nonexistent/.* failed"):
            adapter.get_requisition("nonexistent")

    def test_http_401_triggers_token_refresh_then_retry(self):
        call_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if request.method == "POST" and "token/new" in str(request.url):
                return httpx.Response(200, json=TOKEN_RESPONSE)
            if request.method == "POST" and "token/refresh" in str(request.url):
                return httpx.Response(200, json={
                    "access": "refreshed-token",
                    "access_expires": 86400,
                    "refresh": "new-refresh",
                    "refresh_expires": 2592000,
                })
            if request.method == "GET" and "requisitions" in str(request.url):
                if call_count <= 3:  # first call gets 401
                    return httpx.Response(401, json={"error": "Unauthorized"})
                return httpx.Response(200, json={"id": REQUISITION_ID, "accounts": []})
            return httpx.Response(404)

        client = httpx.Client(transport=httpx.MockTransport(handler))
        adapter = NordigenAdapter(SECRET_ID, SECRET_KEY, client=client)
        result = adapter.get_requisition(REQUISITION_ID)
        assert result["id"] == REQUISITION_ID
        assert adapter._access_token == "refreshed-token"

    def test_http_429_raises_provider_error(self):
        adapter = _adapter({
            ("POST", f"{NordigenAdapter.BASE_URL}/token/new/"): {"body": TOKEN_RESPONSE},
            ("GET", f"{NordigenAdapter.BASE_URL}/accounts/{ACCOUNT_UUID}/transactions/"): {
                "status": 429,
                "body": {"error": "Rate limited"},
            },
        })
        with pytest.raises(ProviderError, match=".*429.*"):
            adapter.fetch_transactions(ACCOUNT_UUID, since=date(2026, 1, 1))


# ------------------------------------------------------------------
# Integration-style: data mapping from realistic API payload
# ------------------------------------------------------------------


class TestDataMapping:
    def test_full_transaction_mapping(self):
        raw = {
            "transactionId": "txn-999",
            "bookingDate": "2026-07-01",
            "valueDate": "2026-06-30",
            "transactionAmount": {"amount": "-250.00", "currency": "EUR"},
            "creditorName": "Landlord GmbH",
            "remittanceInformationUnstructured": "Rent July 2026",
            "remittanceInformationUnstructuredArray": ["Rent July 2026"],
            "bankTransactionCode": "PMNT-CCIP",
            "internalTransactionId": "int-999",
            "additionalInformation": "Monthly rent payment",
        }
        txn = NordigenAdapter._parse_transaction(raw)
        assert txn is not None
        assert txn.external_id == "txn-999"
        assert txn.booking_date == date(2026, 7, 1)
        assert txn.value_date == date(2026, 6, 30)
        assert txn.amount == Decimal("-250.00")
        assert txn.currency == "EUR"
        assert txn.description == "Rent July 2026"
        assert txn.counterparty_name == "Landlord GmbH"
        assert txn.status == "booked"
        assert txn.raw_payload == raw

    def test_transaction_without_booking_date_is_skipped(self):
        raw = {
            "transactionAmount": {"amount": "100.00", "currency": "PLN"},
            "creditorName": "Unknown",
        }
        txn = NordigenAdapter._parse_transaction(raw)
        assert txn is None

    def test_counterparty_prefers_creditor(self):
        raw = {
            "bookingDate": "2026-07-01",
            "transactionAmount": {"amount": "-50.00", "currency": "PLN"},
            "creditorName": "Shop",
            "debtorName": "Me",
        }
        txn = NordigenAdapter._parse_transaction(raw)
        assert txn.counterparty_name == "Shop"

    def test_counterparty_falls_back_to_debtor(self):
        raw = {
            "bookingDate": "2026-07-01",
            "transactionAmount": {"amount": "-50.00", "currency": "PLN"},
            "debtorName": "Me",
        }
        txn = NordigenAdapter._parse_transaction(raw)
        assert txn.counterparty_name == "Me"


# ------------------------------------------------------------------
# Additional NordigenAdapter tests
# ------------------------------------------------------------------


class TestTokenExpired:
    def test_initially_expired(self):
        adapter = NordigenAdapter(secret_id=SECRET_ID, secret_key=SECRET_KEY)
        assert adapter._token_expired() is True

    def test_after_obtain_not_expired(self):
        adapter = _adapter({
            ("POST", f"{NordigenAdapter.BASE_URL}/token/new/"): {
                "body": TOKEN_RESPONSE,
            },
        })
        adapter._obtain_token()
        assert adapter._token_expired() is False


class TestEnsureToken:
    def test_obtains_when_no_token(self):
        adapter = _adapter({
            ("POST", f"{NordigenAdapter.BASE_URL}/token/new/"): {
                "body": TOKEN_RESPONSE,
            },
            ("GET", f"{NordigenAdapter.BASE_URL}/institutions/"): {
                "body": [{"id": "BANK", "name": "Bank"}],
            },
        })
        adapter._ensure_token()
        assert adapter._access_token == "access-token-123"
        # Verify it works for actual requests
        resp = adapter.list_institutions(country="PL")
        assert len(resp) == 1


class TestHeaders:
    def test_returns_authorization_header(self):
        adapter = _adapter({
            ("POST", f"{NordigenAdapter.BASE_URL}/token/new/"): {
                "body": TOKEN_RESPONSE,
            },
        })
        headers = adapter._headers()
        assert headers["Authorization"] == "Bearer access-token-123"


class TestListInstitutions:
    def test_returns_institutions(self):
        mock_data = [
            {"id": "BANK1", "name": "First Bank", "logo": "https://logo.url/1"},
            {"id": "BANK2", "name": "Second Bank"},
        ]
        adapter = _adapter({
            ("POST", f"{NordigenAdapter.BASE_URL}/token/new/"): {
                "body": TOKEN_RESPONSE,
            },
            ("GET", f"{NordigenAdapter.BASE_URL}/institutions/"): {
                "body": mock_data,
            },
        })
        result = adapter.list_institutions(country="PL")
        assert len(result) == 2
        assert result[0]["id"] == "BANK1"
        assert result[1]["id"] == "BANK2"


class TestPostWithRetry:
    def test_401_retries(self):
        call_log: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            call_log.append(str(request.url))
            if "/token/new/" in str(request.url):
                return httpx.Response(200, json={"access": "new-token", "access_expires": 86400})
            # First call to the actual endpoint returns 401
            if call_log.count(str(request.url)) == 1:
                return httpx.Response(401, json={"error": "Unauthorized"})
            return httpx.Response(200, json={"id": "req-retry", "link": "https://link"})

        transport = httpx.MockTransport(handler)
        client = httpx.Client(transport=transport)
        adapter = NordigenAdapter(secret_id=SECRET_ID, secret_key=SECRET_KEY, client=client)

        result = adapter._post("/requisitions/", json={"institution_id": "BANK"})
        assert result["id"] == "req-retry"
        # The 401 triggers a token refresh, then the request is retried.
        # Token call(s) + 1st call (401) + retry (200) = 4 calls
        assert len(call_log) == 4


class TestFetchTransactionsEdgeCases:
    def test_malformed_transaction_skipped(self):
        adapter = _adapter({
            ("POST", f"{NordigenAdapter.BASE_URL}/token/new/"): {
                "body": TOKEN_RESPONSE,
            },
            ("GET", f"{NordigenAdapter.BASE_URL}/accounts/{ACCOUNT_UUID}/transactions/"): {
                "body": {
                    "transactions": {
                        "booked": [{"transactionAmount": {"amount": "100"}}],  # no bookingDate
                    }
                },
            },
        })
        result = adapter.fetch_transactions(ACCOUNT_UUID, date(2026, 1, 1))
        assert result == []


class TestFetchBalancesEdgeCases:
    def test_multiple_types_prefers_interim_available(self):
        mock_balances = {
            "balances": [
                {"balanceType": "closingBooked", "balanceAmount": {"amount": "500"}, "referenceDate": "2026-07-01"},
                {"balanceType": "interimAvailable", "balanceAmount": {"amount": "800"}, "referenceDate": "2026-07-01"},
            ]
        }
        adapter = _adapter({
            ("POST", f"{NordigenAdapter.BASE_URL}/token/new/"): {"body": TOKEN_RESPONSE},
            ("GET", f"{NordigenAdapter.BASE_URL}/accounts/{ACCOUNT_UUID}/balances/"): {
                "body": mock_balances,
            },
        })
        balance, bal_time = adapter.fetch_balances(ACCOUNT_UUID)
        assert balance == Decimal("800")

    def test_no_reference_date(self):
        mock_balances = {
            "balances": [
                {"balanceType": "interimAvailable", "balanceAmount": {"amount": "1000"}},
            ]
        }
        adapter = _adapter({
            ("POST", f"{NordigenAdapter.BASE_URL}/token/new/"): {"body": TOKEN_RESPONSE},
            ("GET", f"{NordigenAdapter.BASE_URL}/accounts/{ACCOUNT_UUID}/balances/"): {
                "body": mock_balances,
            },
        })
        balance, bal_time = adapter.fetch_balances(ACCOUNT_UUID)
        assert balance == Decimal("1000")
        assert bal_time is None


class TestClose:
    def test_close_does_not_raise(self):
        adapter = _adapter({
            ("POST", f"{NordigenAdapter.BASE_URL}/token/new/"): {"body": TOKEN_RESPONSE},
        })
        adapter.close()  # should not raise
