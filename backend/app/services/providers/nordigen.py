import time
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

import httpx

from app.services.providers.base import (
    ProviderAccount,
    ProviderAdapter,
    ProviderTransaction,
)


class ProviderError(Exception):
    """Raised when a provider API call fails (network, auth, unexpected status)."""


_ISO_20022_MAP = {
    "CACC": "checking",
    "SVGS": "savings",
    "CARD": "credit_card",
    "LOAN": "loan",
    "MGLD": "investment",
}


def _map_account_type(iso_code: Optional[str]) -> str:
    return _ISO_20022_MAP.get(iso_code or "") or "other"


def _parse_date(raw: Optional[str]) -> Optional[date]:
    if not raw:
        return None
    try:
        return date.fromisoformat(raw.split("T")[0])
    except (ValueError, TypeError):
        return None


def _parse_datetime(raw: Optional[str]) -> Optional[datetime]:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw)
    except (ValueError, TypeError):
        try:
            return datetime.fromisoformat(raw.split("T")[0])
        except (ValueError, TypeError):
            return None


def _parse_amount(raw_amount: dict) -> Decimal:
    return Decimal(str(raw_amount.get("amount", "0")))


class NordigenAdapter(ProviderAdapter):
    """Adapter for the GoCardless Bank Account Data API (formerly Nordigen).

    API docs: https://developer.gocardless.com/bank-account-data/overview
    Base URL: https://bankaccountdata.gocardless.com/api/v2/
    """

    BASE_URL = "https://bankaccountdata.gocardless.com/api/v2"

    def __init__(
        self,
        secret_id: str,
        secret_key: str,
        base_url: Optional[str] = None,
        client: Optional[httpx.Client] = None,
    ):
        self._secret_id = secret_id
        self._secret_key = secret_key
        self._base_url = (base_url or self.BASE_URL).rstrip("/")
        self._client = client or httpx.Client(timeout=30.0)

        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._token_expires_at: float = 0.0

    # ------------------------------------------------------------------
    # Token management
    # ------------------------------------------------------------------

    def _token_expired(self) -> bool:
        return time.monotonic() >= self._token_expires_at - 60  # 60s safety margin

    def _obtain_token(self) -> None:
        resp = self._client.post(
            f"{self._base_url}/token/new/",
            json={"secret_id": self._secret_id, "secret_key": self._secret_key},
        )
        if resp.status_code != 200:
            raise ProviderError(
                f"Token request failed (HTTP {resp.status_code}): {resp.text}"
            )
        data = resp.json()
        self._access_token = data["access"]
        self._refresh_token = data.get("refresh")
        self._token_expires_at = time.monotonic() + data.get("access_expires", 86400)

    def _refresh_access_token(self) -> None:
        if not self._refresh_token:
            self._obtain_token()
            return
        resp = self._client.post(
            f"{self._base_url}/token/refresh/",
            json={"refresh": self._refresh_token},
        )
        if resp.status_code != 200:
            self._obtain_token()
            return
        data = resp.json()
        self._access_token = data["access"]
        self._refresh_token = data.get("refresh")
        self._token_expires_at = time.monotonic() + data.get("access_expires", 86400)

    def _ensure_token(self) -> None:
        if self._access_token is None:
            self._obtain_token()
        elif self._token_expired():
            self._refresh_access_token()

    def _headers(self) -> dict:
        self._ensure_token()
        return {"Authorization": f"Bearer {self._access_token}"}

    # ------------------------------------------------------------------
    # ProviderAdapter interface
    # ------------------------------------------------------------------

    def authenticate(self) -> str:
        self._obtain_token()
        assert self._access_token is not None
        return self._access_token

    def fetch_accounts(self, requisition_id: str) -> list[ProviderAccount]:
        req = self.get_requisition(requisition_id)
        accounts: list[ProviderAccount] = []

        for acc_id in req.get("accounts", []):
            details = self._get(f"/accounts/{acc_id}/details/").get("account", {})
            balances = self._get(f"/accounts/{acc_id}/balances/").get("balances", [])

            iban = details.get("iban")
            currency = details.get("currency", "EUR")
            name = details.get("name") or details.get("ownerName") or f"Account {acc_id[:8]}"
            iso_type = details.get("cashAccountType")
            acc_type = _map_account_type(iso_type)

            balance, bal_time = self._extract_balance(balances)

            accounts.append(
                ProviderAccount(
                    external_account_id=acc_id,
                    iban=iban,
                    currency=currency,
                    display_name=name,
                    account_type=acc_type,
                    current_balance=balance,
                    balance_as_of=bal_time,
                )
            )

        return accounts

    def fetch_transactions(
        self, external_account_id: str, since: date
    ) -> list[ProviderTransaction]:
        params = {"date_from": since.isoformat(), "date_to": date.today().isoformat()}
        data = self._get(
            f"/accounts/{external_account_id}/transactions/", params=params
        ).get("transactions", {})

        raw_booked = data.get("booked", [])
        raw_pending = data.get("pending", [])

        result: list[ProviderTransaction] = []
        for raw in raw_booked + raw_pending:
            txn = self._parse_transaction(raw)
            if txn is not None:
                result.append(txn)
        return result

    def fetch_balances(
        self, external_account_id: str
    ) -> tuple[Decimal, Optional[datetime]]:
        data = self._get(f"/accounts/{external_account_id}/balances/")
        return self._extract_balance(data.get("balances", []))

    def create_requisition(
        self, institution_id: str, redirect_uri: str, reference: str
    ) -> dict:
        return self._post(
            "/requisitions/",
            json={
                "redirect": redirect_uri,
                "institution_id": institution_id,
                "reference": reference,
                "user_language": "EN",
            },
        )

    def get_requisition(self, requisition_id: str) -> dict:
        return self._get(f"/requisitions/{requisition_id}/")

    def list_institutions(self, country: str = "PL") -> list[dict]:
        return self._get("/institutions/", params={"country": country})

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get(self, path: str, params: Optional[dict] = None) -> dict:
        resp = self._client.get(
            f"{self._base_url}{path}", headers=self._headers(), params=params
        )
        if resp.status_code == 401:
            self._refresh_access_token()
            resp = self._client.get(
                f"{self._base_url}{path}", headers=self._headers(), params=params
            )
        if resp.status_code >= 400:
            raise ProviderError(
                f"GET {path} failed (HTTP {resp.status_code}): {resp.text}"
            )
        return resp.json()

    def _post(self, path: str, json: dict) -> dict:
        resp = self._client.post(
            f"{self._base_url}{path}", headers=self._headers(), json=json
        )
        if resp.status_code == 401:
            self._refresh_access_token()
            resp = self._client.post(
                f"{self._base_url}{path}", headers=self._headers(), json=json
            )
        if resp.status_code >= 400:
            raise ProviderError(
                f"POST {path} failed (HTTP {resp.status_code}): {resp.text}"
            )
        return resp.json()

    @staticmethod
    def _extract_balance(
        balances: list[dict],
    ) -> tuple[Decimal, Optional[datetime]]:
        if not balances:
            return Decimal("0"), None
        preferred_types = ["interimAvailable", "closingBooked", "forwardAvailable", "openingBooked"]
        for bt in preferred_types:
            for b in balances:
                if b.get("balanceType") == bt:
                    amt = _parse_amount(b.get("balanceAmount", {}))
                    ref = _parse_datetime(b.get("referenceDate"))
                    if ref is not None:
                        ref = ref.replace(tzinfo=timezone.utc).astimezone()
                    return amt, ref
        bal = balances[0]
        amt = _parse_amount(bal.get("balanceAmount", {}))
        ref = _parse_datetime(bal.get("referenceDate"))
        if ref is not None:
            ref = ref.replace(tzinfo=timezone.utc).astimezone()
        return amt, ref

    @staticmethod
    def _parse_transaction(raw: dict) -> Optional[ProviderTransaction]:
        tx_id = raw.get("transactionId")
        amt_raw = raw.get("transactionAmount", {})
        amount = _parse_amount(amt_raw)
        currency = amt_raw.get("currency", "EUR")
        booking = _parse_date(raw.get("bookingDate"))
        value = _parse_date(raw.get("valueDate"))
        description = (
            raw.get("remittanceInformationUnstructured")
            or raw.get("remittanceInformationUnstructuredArray", [None])[0]
            or ""
        )

        creditor = raw.get("creditorName")
        debtor = raw.get("debtorName")
        counterparty = creditor or debtor

        status = "pending" if raw.get("pending") else "booked"

        if booking is None:
            return None

        return ProviderTransaction(
            external_id=tx_id,
            amount=amount,
            currency=currency,
            booking_date=booking,
            value_date=value,
            status=status,
            description=description,
            counterparty_name=counterparty,
            raw_payload=raw,
        )

    def close(self) -> None:
        self._client.close()
