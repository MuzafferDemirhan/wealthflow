import time
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

import httpx
import jwt as pyjwt

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


class EnableBankingAdapter(ProviderAdapter):
    """Adapter for the Enable Banking API (https://enablebanking.com).

    API docs: https://enablebanking.com/docs/api/
    Base URL: https://api.enablebanking.com
    Auth: JWT signed with RSA private key (RS256).
    """

    BASE_URL = "https://api.enablebanking.com"

    def __init__(
        self,
        app_id: str,
        private_key_pem: str,
        base_url: Optional[str] = None,
        client: Optional[httpx.Client] = None,
    ):
        self._app_id = app_id
        # Accept either inline PEM or a file path
        if private_key_pem and not private_key_pem.startswith("-----"):
            try:
                private_key_pem = open(private_key_pem, encoding="utf-8").read()
            except (FileNotFoundError, OSError):
                raise ProviderError(
                    f"Enable Banking private key file not found at: {private_key_pem}. "
                    "Set ENABLE_BANKING_PRIVATE_KEY in .env to the PEM content or path."
                )
        self._private_key_pem = private_key_pem.replace("\\n", "\n")
        self._base_url = (base_url or self.BASE_URL).rstrip("/")
        self._client = client or httpx.Client(timeout=30.0)

    # ------------------------------------------------------------------
    # JWT token management
    # ------------------------------------------------------------------

    def _generate_jwt(self) -> str:
        iat = int(time.time())
        return pyjwt.encode(
            {
                "iss": "enablebanking.com",
                "aud": "api.enablebanking.com",
                "iat": iat,
                "exp": iat + 3600,
            },
            self._private_key_pem,
            algorithm="RS256",
            headers={"kid": self._app_id},
        )

    def _headers(self) -> dict:
        if not self._app_id or not self._private_key_pem.strip():
            raise ProviderError(
                "Enable Banking is not configured. "
                "Set ENABLE_BANKING_APP_ID and ENABLE_BANKING_PRIVATE_KEY in .env"
            )
        return {"Authorization": f"Bearer {self._generate_jwt()}"}

    # ------------------------------------------------------------------
    # ProviderAdapter interface
    # ------------------------------------------------------------------

    def authenticate(self) -> str:
        return self._generate_jwt()

    def fetch_accounts(self, session_id: str) -> list[ProviderAccount]:
        session = self.get_requisition(session_id)
        raw_accounts = session.get("accounts_data", session.get("accounts", []))
        accounts: list[ProviderAccount] = []

        for acc in raw_accounts:
            uid = acc.get("uid", "")
            if not uid:
                continue

            details = acc.get("account_id", {})
            iban = details.get("iban")
            currency = acc.get("currency", "EUR")
            name = acc.get("name") or f"Account {uid[:8]}"
            iso_type = acc.get("cash_account_type")
            acc_type = _map_account_type(iso_type)

            balance, bal_time = self._fetch_balance_for_account(uid)

            accounts.append(
                ProviderAccount(
                    external_account_id=uid,
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
        params = {
            "date_from": since.isoformat(),
            "date_to": date.today().isoformat(),
        }
        data = self._get(
            f"/accounts/{external_account_id}/transactions", params=params
        )
        raw_transactions = data.get("transactions", [])
        continuation_key = data.get("continuation_key")

        result: list[ProviderTransaction] = []
        for raw in raw_transactions:
            txn = self._parse_transaction(raw)
            if txn is not None:
                result.append(txn)

        while continuation_key:
            params["continuation_key"] = continuation_key
            data = self._get(
                f"/accounts/{external_account_id}/transactions", params=params
            )
            raw_transactions = data.get("transactions", [])
            continuation_key = data.get("continuation_key")
            for raw in raw_transactions:
                txn = self._parse_transaction(raw)
                if txn is not None:
                    result.append(txn)

        return result

    def fetch_balances(
        self, external_account_id: str
    ) -> tuple[Decimal, Optional[datetime]]:
        return self._fetch_balance_for_account(external_account_id)

    def create_requisition(
        self, institution_id: str, redirect_uri: str, reference: str
    ) -> dict:
        parts = institution_id.split("|")
        name = parts[0]
        country = parts[1] if len(parts) > 1 else "PL"

        valid_until = (
            datetime.now(timezone.utc).replace(microsecond=0)
            + timedelta(days=90)
        ).isoformat()

        return self._post(
            "/auth",
            json={
                "access": {"valid_until": valid_until},
                "aspsp": {"name": name, "country": country},
                "state": reference,
                "redirect_url": redirect_uri,
                "psu_type": "personal",
                "language": "en",
            },
        )

    def get_requisition(self, session_id: str) -> dict:
        return self._get(f"/sessions/{session_id}")

    def list_institutions(self, country: str = "PL") -> list[dict]:
        return self._get("/aspsps", params={"country": country}).get("aspsps", [])

    def authorize_session(self, code: str) -> dict:
        """Exchange an authorization code for a full session (requisition)."""
        return self._post("/sessions", json={"code": code})

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get(self, path: str, params: Optional[dict] = None) -> dict:
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
        if resp.status_code >= 400:
            raise ProviderError(
                f"POST {path} failed (HTTP {resp.status_code}): {resp.text}"
            )
        return resp.json()

    def _fetch_balance_for_account(
        self, account_uid: str
    ) -> tuple[Decimal, Optional[datetime]]:
        try:
            data = self._get(f"/accounts/{account_uid}/balances")
            return self._extract_balance(data.get("balances", []))
        except ProviderError:
            return Decimal("0"), None

    @staticmethod
    def _extract_balance(
        balances: list[dict],
    ) -> tuple[Decimal, Optional[datetime]]:
        if not balances:
            return Decimal("0"), None

        preferred = ["CLAV", "XPCD", "CLBD", "ITAV"]
        for bt in preferred:
            for b in balances:
                if b.get("balance_type") == bt or b.get("balanceType") == bt:
                    amt = _parse_amount(
                        b.get("balance_amount") or b.get("balanceAmount", {})
                    )
                    ref = _parse_datetime(
                        b.get("last_change_date_time")
                        or b.get("reference_date")
                        or b.get("lastChangeDateTime")
                    )
                    if ref is not None:
                        ref = ref.replace(tzinfo=timezone.utc).astimezone()
                    return amt, ref
        bal = balances[0]
        amt = _parse_amount(
            bal.get("balance_amount") or bal.get("balanceAmount", {})
        )
        ref = _parse_datetime(
            bal.get("last_change_date_time")
            or bal.get("reference_date")
            or bal.get("lastChangeDateTime")
        )
        if ref is not None:
            ref = ref.replace(tzinfo=timezone.utc).astimezone()
        return amt, ref

    @staticmethod
    def _parse_transaction(raw: dict) -> Optional[ProviderTransaction]:
        tx_id = raw.get("transaction_id") or raw.get("transactionId") or raw.get("entry_reference")
        amt_raw = raw.get("transaction_amount") or raw.get("transactionAmount", {})
        amount = _parse_amount(amt_raw)
        currency = amt_raw.get("currency", "EUR")
        booking = _parse_date(raw.get("booking_date") or raw.get("bookingDate"))
        value = _parse_date(raw.get("value_date") or raw.get("valueDate"))
        description = (
            raw.get("remittance_information", [None])[0]
            or raw.get("remittanceInformation", "")
            or raw.get("remittanceInformationUnstructured")
            or ""
        )

        creditor = raw.get("creditor_name") or raw.get("creditorName")
        debtor = raw.get("debtor_name") or raw.get("debtorName")
        counterparty = creditor or debtor

        status_raw = raw.get("status") or raw.get("transaction_status") or "BOOK"
        status = "pending" if status_raw.upper() in ("PDNG", "PENDING") else "booked"

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
