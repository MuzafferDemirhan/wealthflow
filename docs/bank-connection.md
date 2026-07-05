# Plaid Integration Plan — WealthFlow
**Branch:** `feature/bank-connection-api`  
**Target:** Add Plaid as a second `ProviderAdapter` alongside the existing EnableBanking adapter, following the adapter pattern already established in `backend/app/services/providers/base.py`.

---

## 0. Context & Constraints

| Item | Detail |
|---|---|
| Existing pattern | `ProviderAdapter` ABC in `base.py`. `EnableBankingAdapter` is the reference implementation. `connect_service.py` is provider-agnostic once it receives an adapter instance. |
| DB model | `BankConnection.provider` is already `BankProvider.PLAID` enum value — model is ready. |
| Auth flow difference | EnableBanking uses a redirect + authorization code. Plaid uses **Link token → public token → access token** (Plaid Link SDK). The connect service layer must be extended to accommodate this. |
| Region | Plaid supports US/EU/UK. EnableBanking targets EU. Both coexist. |
| Security principle | Access tokens **never** leave the backend. Frontend only handles `link_token` and `public_token`. |

---

## 1. Dependencies

### Step 1.1 — Add `plaid-python` to requirements

**File:** `backend/requirements.txt`

```
plaid-python==25.2.0
```

**Rationale:** Official Plaid Python SDK. Handles OAuth, retry logic, and response parsing.

---

## 2. Configuration

### Step 2.1 — Extend `Settings` in `config.py`

**File:** `backend/app/core/config.py`

Add to the `Settings` class:

```python
# Plaid
PLAID_CLIENT_ID: str = ""
PLAID_SECRET: str = ""
PLAID_ENV: str = "sandbox"          # sandbox | development | production
PLAID_PRODUCTS: list[str] = ["transactions"]
PLAID_COUNTRY_CODES: list[str] = ["US", "GB", "NL", "PL"]
```

**Security note:** `PLAID_SECRET` must only exist in `.env` — never hardcoded, never logged, never returned in any API response.

### Step 2.2 — Add to `.env.example`

```
PLAID_CLIENT_ID=
PLAID_SECRET=
PLAID_ENV=sandbox
PLAID_PRODUCTS=transactions
PLAID_COUNTRY_CODES=US,GB,NL,PL
```

---

## 3. Provider Adapter

### Step 3.1 — Create `backend/app/services/providers/plaid.py`

This is the main implementation step. Follow the `ProviderAdapter` ABC exactly.

```python
"""
Plaid provider adapter.

Auth flow:
  1. Backend creates a link_token  → returned to frontend
  2. Frontend opens Plaid Link SDK → user authenticates with their bank
  3. Frontend receives public_token → POSTs it to our backend
  4. Backend exchanges public_token for access_token (never leaves backend)
  5. Backend calls /accounts/get and /transactions/sync with access_token
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

import plaid
from plaid.api import plaid_api
from plaid.model.accounts_get_request import AccountsGetRequest
from plaid.model.country_code import CountryCode
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.products import Products
from plaid.model.transactions_sync_request import TransactionsSyncRequest

from app.services.providers.base import ProviderAccount, ProviderAdapter, ProviderTransaction

logger = logging.getLogger(__name__)


class PlaidProviderError(Exception):
    """Raised when a Plaid API call fails."""


_PLAID_ACCOUNT_TYPE_MAP = {
    "depository": {
        "checking": "checking",
        "savings": "savings",
        "money market": "savings",
        "cd": "savings",
        "paypal": "other",
    },
    "credit": "credit_card",
    "loan": "loan",
    "investment": "investment",
}


def _map_plaid_account_type(acc_type: str, acc_subtype: Optional[str]) -> str:
    mapped = _PLAID_ACCOUNT_TYPE_MAP.get(acc_type)
    if isinstance(mapped, dict):
        return mapped.get(acc_subtype or "", "other")
    return mapped or "other"


def _build_plaid_client(client_id: str, secret: str, env: str) -> plaid_api.PlaidApi:
    env_map = {
        "sandbox": plaid.Environment.Sandbox,
        "development": plaid.Environment.Development,
        "production": plaid.Environment.Production,
    }
    plaid_env = env_map.get(env.lower(), plaid.Environment.Sandbox)
    configuration = plaid.Configuration(
        host=plaid_env,
        api_key={"clientId": client_id, "secret": secret},
    )
    api_client = plaid.ApiClient(configuration)
    return plaid_api.PlaidApi(api_client)


class PlaidAdapter(ProviderAdapter):
    """
    Adapter for the Plaid API.

    This adapter holds an access_token per institution link (one per BankConnection).
    It does NOT store state; the access_token is passed in at call time,
    retrieved from BankConnection.external_reference (encrypted at rest).
    """

    def __init__(
        self,
        client_id: str,
        secret: str,
        env: str = "sandbox",
        products: Optional[list[str]] = None,
        country_codes: Optional[list[str]] = None,
    ):
        if not client_id or not secret:
            raise PlaidProviderError(
                "Plaid is not configured. Set PLAID_CLIENT_ID and PLAID_SECRET in .env"
            )
        self._client = _build_plaid_client(client_id, secret, env)
        self._products = [Products(p) for p in (products or ["transactions"])]
        self._country_codes = [CountryCode(c) for c in (country_codes or ["US"])]

    # ------------------------------------------------------------------
    # Link token (Step 1 of Plaid Link flow)
    # ------------------------------------------------------------------

    def create_link_token(self, user_id: str, redirect_uri: Optional[str] = None) -> str:
        """
        Create a link_token for the Plaid Link SDK.
        `user_id` is the WealthFlow user UUID as a string (used as Plaid client_user_id).
        Returns the link_token string.
        """
        request = LinkTokenCreateRequest(
            products=self._products,
            client_name="WealthFlow",
            country_codes=self._country_codes,
            language="en",
            user=LinkTokenCreateRequestUser(client_user_id=user_id),
        )
        if redirect_uri:
            request.redirect_uri = redirect_uri

        try:
            response = self._client.link_token_create(request)
            return response["link_token"]
        except plaid.ApiException as exc:
            raise PlaidProviderError(f"Failed to create link token: {exc.body}") from exc

    # ------------------------------------------------------------------
    # Token exchange (Step 2: public_token → access_token)
    # ------------------------------------------------------------------

    def exchange_public_token(self, public_token: str) -> tuple[str, str]:
        """
        Exchange a public_token for (access_token, item_id).
        access_token must be stored encrypted in BankConnection.external_reference.
        NEVER log or return access_token to the frontend.
        """
        try:
            response = self._client.item_public_token_exchange(
                ItemPublicTokenExchangeRequest(public_token=public_token)
            )
            return response["access_token"], response["item_id"]
        except plaid.ApiException as exc:
            raise PlaidProviderError(f"Token exchange failed: {exc.body}") from exc

    # ------------------------------------------------------------------
    # ProviderAdapter interface
    # ------------------------------------------------------------------

    def authenticate(self) -> str:
        # Plaid uses per-request client_id+secret; no global session token.
        return "plaid-client-credentials"

    def fetch_accounts(self, access_token: str) -> list[ProviderAccount]:
        """
        `access_token` is stored in BankConnection.external_reference (encrypted).
        """
        try:
            response = self._client.accounts_get(AccountsGetRequest(access_token=access_token))
        except plaid.ApiException as exc:
            raise PlaidProviderError(f"accounts/get failed: {exc.body}") from exc

        accounts: list[ProviderAccount] = []
        for acc in response["accounts"]:
            balance = acc["balances"]
            current = Decimal(str(balance.get("current") or 0))
            acc_type = _map_plaid_account_type(
                str(acc.get("type", "")), str(acc.get("subtype", ""))
            )
            accounts.append(
                ProviderAccount(
                    external_account_id=acc["account_id"],
                    iban=None,  # Plaid does not expose IBAN
                    currency=(balance.get("iso_currency_code") or "USD").upper(),
                    display_name=acc.get("name") or f"Account {acc['account_id'][:8]}",
                    account_type=acc_type,
                    current_balance=current,
                    balance_as_of=datetime.now(timezone.utc),
                )
            )
        return accounts

    def fetch_transactions(
        self, external_account_id: str, since: date
    ) -> list[ProviderTransaction]:
        """
        NOTE: `external_account_id` here is used as a filter after fetching all
        transactions for the item. Plaid's /transactions/sync works at item level.
        Pass `access_token` via `external_account_id` using the format
        `{access_token}::{account_id}` — parsed internally.

        This dual-encoding is a consequence of the ProviderAdapter interface
        being designed for account-scoped fetches. A future refactor can add
        an optional `context` param to the ABC.
        """
        # Parse encoded value
        if "::" in external_account_id:
            access_token, account_id = external_account_id.split("::", 1)
        else:
            raise PlaidProviderError(
                "PlaidAdapter.fetch_transactions requires 'access_token::account_id' format"
            )

        all_txns = self._sync_all_transactions(access_token)
        # Filter to only this account and date range
        result = []
        for txn in all_txns:
            if txn.external_id and account_id and txn.raw_payload.get("account_id") != account_id:
                continue
            if txn.booking_date < since:
                continue
            result.append(txn)
        return result

    def fetch_balances(
        self, external_account_id: str
    ) -> tuple[Decimal, Optional[datetime]]:
        # For Plaid, balance is fetched as part of fetch_accounts.
        # This method exists to satisfy the ABC but is not called in the main flow.
        return Decimal("0"), None

    def create_requisition(
        self, institution_id: str, redirect_uri: str, reference: str
    ) -> dict:
        # For Plaid, "creating a requisition" means creating a link_token.
        # `user_id` is embedded in `reference` (the UUID we generate in connect_service).
        link_token = self.create_link_token(user_id=reference, redirect_uri=redirect_uri)
        return {
            "link_token": link_token,   # frontend uses this to open Plaid Link
            "url": None,                 # Plaid Link is SDK-based, not a redirect URL
            "authorization_id": reference,
        }

    def get_requisition(self, requisition_id: str) -> dict:
        # Plaid does not have a "requisition" concept.
        # After token exchange, the connection is immediately LINKED.
        return {"status": "AUTHORIZED"}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _sync_all_transactions(self, access_token: str) -> list[ProviderTransaction]:
        """
        Use /transactions/sync (cursor-based, recommended by Plaid).
        Fetches all added transactions (not modified/removed for now).
        """
        transactions = []
        cursor = None

        while True:
            try:
                req = TransactionsSyncRequest(access_token=access_token)
                if cursor:
                    req.cursor = cursor
                response = self._client.transactions_sync(req)
            except plaid.ApiException as exc:
                raise PlaidProviderError(f"transactions/sync failed: {exc.body}") from exc

            for txn in response["added"]:
                parsed = self._parse_plaid_transaction(txn)
                if parsed:
                    transactions.append(parsed)

            if not response["has_more"]:
                break
            cursor = response["next_cursor"]

        return transactions

    @staticmethod
    def _parse_plaid_transaction(raw: dict) -> Optional[ProviderTransaction]:
        amount_raw = raw.get("amount")
        if amount_raw is None:
            return None
        # Plaid amounts: positive = debit (money out), negative = credit (money in)
        # WealthFlow convention: negative = expense, positive = income — flip sign
        amount = Decimal(str(amount_raw)) * -1

        booking_raw = raw.get("date")
        if not booking_raw:
            return None
        try:
            booking = date.fromisoformat(booking_raw)
        except ValueError:
            return None

        return ProviderTransaction(
            external_id=raw.get("transaction_id"),
            amount=amount,
            currency=(raw.get("iso_currency_code") or "USD").upper(),
            booking_date=booking,
            value_date=None,
            status="pending" if raw.get("pending") else "booked",
            description=raw.get("name") or raw.get("original_description") or "",
            counterparty_name=raw.get("merchant_name") or raw.get("name"),
            raw_payload=raw,
        )
```

---

## 4. Extend `connect_service.py`

The service layer needs to know which adapter to build based on the requested provider.

### Step 4.1 — Add `_build_plaid_provider()` factory

**File:** `backend/app/services/connect_service.py`

Add import:
```python
from app.services.providers.plaid import PlaidAdapter, PlaidProviderError
```

Add factory function:
```python
def _build_plaid_provider() -> PlaidAdapter:
    return PlaidAdapter(
        client_id=settings.PLAID_CLIENT_ID,
        secret=settings.PLAID_SECRET,
        env=settings.PLAID_ENV,
        products=settings.PLAID_PRODUCTS,
        country_codes=settings.PLAID_COUNTRY_CODES,
    )
```

### Step 4.2 — Add `create_plaid_link_token()` service function

This is a new function — Plaid's link_token step has no equivalent in EnableBanking.

```python
def create_plaid_link_token(
    *,
    user_id: uuid.UUID,
    redirect_uri: Optional[str] = None,
) -> dict:
    """
    Step 1 of Plaid Link: create a link_token for the frontend SDK.
    Returns {"link_token": "..."}.
    """
    try:
        provider = _build_plaid_provider()
        link_token = provider.create_link_token(
            user_id=str(user_id),
            redirect_uri=redirect_uri,
        )
    except PlaidProviderError as exc:
        raise ConnectError(f"Failed to create Plaid link token: {exc}") from exc
    return {"link_token": link_token}
```

### Step 4.3 — Add `exchange_plaid_public_token()` service function

```python
def exchange_plaid_public_token(
    db: Session,
    *,
    user_id: uuid.UUID,
    public_token: str,
    institution_id: str,
    institution_name: str,
) -> dict:
    """
    Step 2 of Plaid Link: exchange public_token → access_token.
    Stores access_token ENCRYPTED in BankConnection.external_reference.
    Creates accounts immediately (Plaid is synchronous after exchange).
    """
    try:
        provider = _build_plaid_provider()
        access_token, item_id = provider.exchange_public_token(public_token)
    except PlaidProviderError as exc:
        raise ConnectError(f"Plaid token exchange failed: {exc}") from exc

    # Store access_token encrypted (see Step 5 for encryption)
    encrypted_token = _encrypt_token(access_token)

    conn = BankConnection(
        user_id=user_id,
        provider=BankProvider.PLAID,
        institution_id=institution_id,
        institution_name=institution_name,
        external_reference=encrypted_token,   # encrypted access_token
        status=ConnectionStatus.LINKED,
    )
    db.add(conn)
    db.commit()
    db.refresh(conn)

    # Sync accounts immediately
    accounts_created = _sync_plaid_accounts(db, conn, provider, access_token)

    return {
        "id": conn.id,
        "status": conn.status,
        "institution_id": conn.institution_id,
        "institution_name": conn.institution_name,
        "accounts_created": accounts_created,
        "item_id": item_id,
    }
```

### Step 4.4 — Add `_sync_plaid_accounts()` helper

```python
def _sync_plaid_accounts(
    db: Session,
    conn: BankConnection,
    provider: PlaidAdapter,
    access_token: str,
) -> list[uuid.UUID]:
    """Fetch Plaid accounts and create Account rows."""
    created: list[uuid.UUID] = []
    try:
        provider_accounts = provider.fetch_accounts(access_token)
    except PlaidProviderError:
        logger.exception("Failed to fetch Plaid accounts for connection %s", conn.id)
        return created

    for pa in provider_accounts:
        existing = db.scalar(
            select(Account).where(
                Account.external_account_id == pa.external_account_id,
                Account.user_id == conn.user_id,
            )
        )
        if existing is not None:
            continue

        try:
            atype = AccountType(pa.account_type)
        except ValueError:
            atype = AccountType.OTHER

        acc = Account(
            user_id=conn.user_id,
            bank_connection_id=conn.id,
            external_account_id=pa.external_account_id,
            display_name=pa.display_name,
            account_type=atype,
            iban=pa.iban,
            currency=pa.currency,
            current_balance=pa.current_balance,
            balance_as_of=pa.balance_as_of,
        )
        db.add(acc)
        db.flush()
        created.append(acc.id)

    if created:
        db.commit()
    return created
```

---

## 5. Token Encryption at Rest

**This is a critical security requirement.** Plaid access tokens are long-lived credentials. Storing them plaintext in the DB is unacceptable.

### Step 5.1 — Add `cryptography` to requirements

```
cryptography==42.0.8
```

### Step 5.2 — Add `TOKEN_ENCRYPTION_KEY` to config

**File:** `backend/app/core/config.py`

```python
TOKEN_ENCRYPTION_KEY: str = ""   # 32-byte URL-safe base64 key; generate with Fernet.generate_key()
```

**`.env.example`:**
```
TOKEN_ENCRYPTION_KEY=   # python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Step 5.3 — Create `backend/app/core/encryption.py`

```python
"""
Symmetric encryption for sensitive values stored in the DB (e.g. Plaid access_token).
Uses Fernet (AES-128-CBC + HMAC-SHA256). Keys must be stored in environment variables.
"""
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def _get_fernet() -> Fernet:
    key = settings.TOKEN_ENCRYPTION_KEY
    if not key:
        raise RuntimeError(
            "TOKEN_ENCRYPTION_KEY is not set. "
            "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    return Fernet(key.encode())


def encrypt_token(plaintext: str) -> str:
    """Encrypt a sensitive string. Returns a URL-safe base64 ciphertext string."""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_token(ciphertext: str) -> str:
    """Decrypt a previously encrypted string. Raises ValueError on tamper/wrong key."""
    try:
        return _get_fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Token decryption failed — possible key mismatch or data corruption") from exc
```

### Step 5.4 — Wire encryption into connect_service

In `connect_service.py`:

```python
from app.core.encryption import encrypt_token as _encrypt_token, decrypt_token as _decrypt_token
```

Wherever a Plaid access_token is read back for API calls:

```python
access_token = _decrypt_token(conn.external_reference)
```

---

## 6. Ingestion Task — Plaid Support

**File:** `backend/app/tasks/ingestion.py`

The existing ingestion Celery task uses `EnableBankingAdapter`. It needs to branch on `conn.provider`.

### Step 6.1 — Extend the ingestion task

Locate the section that builds the provider and add:

```python
from app.models.bank_connection import BankProvider
from app.core.encryption import decrypt_token
from app.services.providers.plaid import PlaidAdapter

def _build_adapter_for_connection(conn: BankConnection):
    if conn.provider == BankProvider.PLAID:
        return PlaidAdapter(
            client_id=settings.PLAID_CLIENT_ID,
            secret=settings.PLAID_SECRET,
            env=settings.PLAID_ENV,
        ), decrypt_token(conn.external_reference)   # returns (adapter, access_token)
    else:
        from app.services.providers.enable_banking import EnableBankingAdapter
        return EnableBankingAdapter(
            app_id=settings.ENABLE_BANKING_APP_ID,
            private_key_pem=settings.ENABLE_BANKING_PRIVATE_KEY,
        ), conn.external_reference
```

For `fetch_transactions` with Plaid, encode the access_token into the account ID:

```python
if conn.provider == BankProvider.PLAID:
    encoded_id = f"{access_token}::{account.external_account_id}"
    transactions = adapter.fetch_transactions(encoded_id, since=since_date)
else:
    transactions = adapter.fetch_transactions(account.external_account_id, since=since_date)
```

---

## 7. API Schemas

### Step 7.1 — Add Plaid schemas to `backend/app/schemas/connect.py`

```python
class PlaidLinkTokenRequest(BaseModel):
    redirect_uri: Optional[str] = None

class PlaidLinkTokenResponse(BaseModel):
    link_token: str

class PlaidExchangeRequest(BaseModel):
    public_token: str
    institution_id: str
    institution_name: str

class PlaidExchangeResponse(BaseModel):
    id: uuid.UUID
    status: str
    institution_id: str
    institution_name: str
    accounts_created: list[uuid.UUID]
```

---

## 8. API Endpoints

### Step 8.1 — Add Plaid routes to `backend/app/api/v1/endpoints/connect.py`

```python
from app.schemas.connect import (
    PlaidLinkTokenRequest,
    PlaidLinkTokenResponse,
    PlaidExchangeRequest,
    PlaidExchangeResponse,
)

@router.post("/plaid/link-token", response_model=PlaidLinkTokenResponse)
async def create_plaid_link_token(
    payload: PlaidLinkTokenRequest,
    current_user: User = Depends(get_current_active_user),
):
    """
    Step 1: Create a Plaid link_token for the frontend Plaid Link SDK.
    The link_token is short-lived (30 min) and single-use.
    """
    try:
        return connect_service.create_plaid_link_token(
            user_id=current_user.id,
            redirect_uri=payload.redirect_uri,
        )
    except connect_service.ConnectError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))


@router.post("/plaid/exchange", response_model=PlaidExchangeResponse, status_code=status.HTTP_201_CREATED)
async def exchange_plaid_token(
    payload: PlaidExchangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Step 2: Exchange the public_token received from Plaid Link for an access_token.
    The public_token is EPHEMERAL — it must be exchanged immediately.
    The access_token is stored encrypted; it is never returned to the client.
    """
    try:
        return connect_service.exchange_plaid_public_token(
            db,
            user_id=current_user.id,
            public_token=payload.public_token,
            institution_id=payload.institution_id,
            institution_name=payload.institution_name,
        )
    except connect_service.ConnectError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
```

---

## 9. Frontend Integration

The frontend already has the Connect page and Plaid is SDK-based (not a redirect).

### Step 9.1 — Install Plaid Link React SDK

```bash
cd frontend
npm install react-plaid-link
```

### Step 9.2 — Create `frontend/src/lib/plaid.ts`

```typescript
export interface PlaidLinkConfig {
  linkToken: string;
  onSuccess: (publicToken: string, metadata: PlaidSuccessMetadata) => void;
  onExit?: () => void;
}

export interface PlaidSuccessMetadata {
  institution: { institution_id: string; name: string };
  accounts: Array<{ id: string; name: string; type: string }>;
}
```

### Step 9.3 — Create `frontend/src/components/PlaidLinkButton.tsx`

```typescript
"use client";

import { useCallback, useEffect, useState } from "react";
import { usePlaidLink } from "react-plaid-link";
import { apiClient } from "@/lib/api-client";

interface Props {
  onSuccess: (publicToken: string, institutionId: string, institutionName: string) => void;
  onError?: (error: string) => void;
}

export function PlaidLinkButton({ onSuccess, onError }: Props) {
  const [linkToken, setLinkToken] = useState<string | null>(null);

  useEffect(() => {
    apiClient
      .post<{ link_token: string }>("/connect/plaid/link-token", {})
      .then((res) => setLinkToken(res.link_token))
      .catch(() => onError?.("Failed to initialize bank connection"));
  }, []);

  const { open, ready } = usePlaidLink({
    token: linkToken ?? "",
    onSuccess: (publicToken, metadata) => {
      const inst = metadata.institution;
      onSuccess(publicToken, inst?.institution_id ?? "", inst?.name ?? "Unknown");
    },
    onExit: (err) => {
      if (err) onError?.("Connection cancelled or failed");
    },
  });

  return (
    <button
      onClick={() => open()}
      disabled={!ready || !linkToken}
      className="..."
    >
      Connect Bank Account (Plaid)
    </button>
  );
}
```

### Step 9.4 — Wire into `/connect/institutions` page

After Plaid Link `onSuccess`:

```typescript
async function handlePlaidSuccess(
  publicToken: string,
  institutionId: string,
  institutionName: string
) {
  await apiClient.post("/connect/plaid/exchange", {
    public_token: publicToken,
    institution_id: institutionId,
    institution_name: institutionName,
  });
  router.push("/connect"); // redirect to connections list
}
```

**Security:** The `publicToken` goes directly to the backend via an authenticated API call. It is never stored in localStorage, sessionStorage, or any state that persists across sessions.

---

## 10. Alembic Migration

`BankConnection.provider` already has `PLAID` in the enum. But if the DB enum was created with only `enable_banking`, it needs updating.

### Step 10.1 — Generate migration

```bash
docker compose exec backend alembic revision --autogenerate -m "add_plaid_to_bank_provider_enum"
```

### Step 10.2 — Review and adjust generated migration

For MS SQL Server, enum changes are handled via `VARCHAR` with a `CHECK` constraint. Verify the generated migration alters the constraint to allow `plaid` as a valid value. If autogenerate misses it, write manually:

```python
def upgrade():
    op.execute("""
        ALTER TABLE bank_connection
        DROP CONSTRAINT IF EXISTS ck_bank_connection_provider;
    """)
    op.execute("""
        ALTER TABLE bank_connection
        ADD CONSTRAINT ck_bank_connection_provider
        CHECK (provider IN ('enable_banking', 'plaid'));
    """)

def downgrade():
    op.execute("""
        ALTER TABLE bank_connection
        DROP CONSTRAINT IF EXISTS ck_bank_connection_provider;
    """)
    op.execute("""
        ALTER TABLE bank_connection
        ADD CONSTRAINT ck_bank_connection_provider
        CHECK (provider IN ('enable_banking'));
    """)
```

---

## 11. Tests

All tests go in `backend/tests/`. Follow the existing pattern in `test_connect.py`.

### Step 11.1 — Unit tests: `tests/test_plaid_adapter.py`

Test the adapter in isolation with mocked Plaid SDK responses.

```
- test_create_link_token_success
- test_create_link_token_missing_credentials_raises
- test_exchange_public_token_success
- test_exchange_public_token_api_error_raises
- test_fetch_accounts_success
- test_fetch_accounts_maps_type_correctly (depository/checking → checking, credit → credit_card)
- test_fetch_transactions_sync_pagination (has_more loop)
- test_parse_plaid_transaction_flips_sign (positive Plaid amount → negative WealthFlow)
- test_parse_plaid_transaction_pending_status
- test_parse_plaid_transaction_missing_date_returns_none
```

### Step 11.2 — Unit tests: `tests/test_encryption.py`

```
- test_encrypt_decrypt_roundtrip
- test_decrypt_tampered_data_raises_value_error
- test_missing_key_raises_runtime_error
```

### Step 11.3 — Service layer tests: `tests/test_connect_service_plaid.py`

Mock `PlaidAdapter` using `unittest.mock.patch`.

```
- test_create_plaid_link_token_returns_token
- test_create_plaid_link_token_provider_error_raises_connect_error
- test_exchange_public_token_creates_connection_and_accounts
- test_exchange_public_token_stores_encrypted_token (assert stored value != raw access_token)
- test_exchange_public_token_provider_error_raises_connect_error
```

### Step 11.4 — API integration tests: `tests/test_connect_api_plaid.py`

Use the existing `client` fixture pattern.

```
- test_create_link_token_endpoint_requires_auth
- test_create_link_token_endpoint_success
- test_exchange_endpoint_requires_auth
- test_exchange_endpoint_success_returns_201
- test_exchange_endpoint_provider_error_returns_502
```

### Step 11.5 — Run tests

```bash
docker compose exec backend pytest tests/test_plaid_adapter.py tests/test_encryption.py tests/test_connect_service_plaid.py tests/test_connect_api_plaid.py -v --cov=app
```

---

## 12. CI/CD

### Step 12.1 — Add `PLAID_CLIENT_ID` and `PLAID_SECRET` as GitHub Secrets

In GitHub repo → Settings → Secrets → Actions:
- `PLAID_CLIENT_ID` → sandbox client id
- `PLAID_SECRET` → sandbox secret
- `TOKEN_ENCRYPTION_KEY` → generated Fernet key

### Step 12.2 — Update `.github/workflows/ci.yml`

In the backend test job, add env vars:

```yaml
env:
  PLAID_CLIENT_ID: ${{ secrets.PLAID_CLIENT_ID }}
  PLAID_SECRET: ${{ secrets.PLAID_SECRET }}
  PLAID_ENV: sandbox
  TOKEN_ENCRYPTION_KEY: ${{ secrets.TOKEN_ENCRYPTION_KEY }}
```

---

## 13. Security Checklist

| Requirement | Implementation |
|---|---|
| Access token never in API response | `exchange_plaid_public_token()` returns only `id`, `status`, account list |
| Access token encrypted at rest | Fernet symmetric encryption in `encryption.py` |
| Public token not stored | Used once in service call, discarded immediately |
| Link token short-lived | Plaid enforces 30-min TTL natively |
| All Plaid endpoints require JWT auth | `Depends(get_current_active_user)` on both routes |
| User can only access own connections | `user_id` filter on all DB queries |
| Secrets in env only | `.env.example` has placeholders; CI uses GitHub Secrets |
| No secrets in logs | `PlaidProviderError` logs `exc.body` which Plaid sanitizes; never log `access_token` |
| Disconnect revokes locally | `disconnect_connection()` sets `status=REVOKED`; optionally call Plaid `/item/remove` |

### Step 13.1 — Optional: Revoke Plaid item on disconnect

In `connect_service.disconnect_connection()`, add:

```python
if conn.provider == BankProvider.PLAID:
    try:
        provider = _build_plaid_provider()
        access_token = _decrypt_token(conn.external_reference)
        provider.revoke_item(access_token)   # calls /item/remove
    except Exception:
        logger.warning("Failed to revoke Plaid item for connection %s", conn.id)
        # Do not block disconnect even if revocation fails
```

Add `revoke_item()` to `PlaidAdapter`:

```python
def revoke_item(self, access_token: str) -> None:
    from plaid.model.item_remove_request import ItemRemoveRequest
    try:
        self._client.item_remove(ItemRemoveRequest(access_token=access_token))
    except plaid.ApiException as exc:
        raise PlaidProviderError(f"item/remove failed: {exc.body}") from exc
```

---

## 14. Implementation Order for Code Agent

Execute steps in this exact sequence:

```
1.  requirements.txt         → add plaid-python, cryptography
2.  config.py                → add PLAID_* and TOKEN_ENCRYPTION_KEY settings
3.  .env.example             → add Plaid + encryption key placeholders
4.  core/encryption.py       → create Fernet encrypt/decrypt module
5.  providers/plaid.py       → create PlaidAdapter (full implementation)
6.  connect_service.py       → add _build_plaid_provider, create_plaid_link_token,
                               exchange_plaid_public_token, _sync_plaid_accounts,
                               import encryption helpers, extend disconnect_connection
7.  tasks/ingestion.py       → extend _build_adapter_for_connection, handle Plaid fetch_transactions
8.  schemas/connect.py       → add Plaid request/response schemas
9.  api/v1/endpoints/connect.py → add /plaid/link-token and /plaid/exchange routes
10. Alembic migration        → add plaid to provider enum CHECK constraint
11. tests/test_plaid_adapter.py        → unit tests for adapter
12. tests/test_encryption.py           → unit tests for encryption
13. tests/test_connect_service_plaid.py → service layer tests
14. tests/test_connect_api_plaid.py    → API integration tests
15. frontend: npm install react-plaid-link
16. frontend/src/lib/plaid.ts          → TypeScript types
17. frontend/src/components/PlaidLinkButton.tsx → SDK component
18. frontend connect page              → wire PlaidLinkButton + exchange call
19. .github/workflows/ci.yml           → add env secrets
20. GitHub repo settings               → add PLAID_CLIENT_ID, PLAID_SECRET, TOKEN_ENCRYPTION_KEY secrets
```

---

## 15. Verification

After implementation, verify end-to-end in sandbox:

1. `POST /connect/plaid/link-token` → returns `link_token`
2. Open Plaid Link in browser with that token → use sandbox credentials (`user_good` / `pass_good`)
3. Plaid Link calls `onSuccess` with `public_token`
4. `POST /connect/plaid/exchange` with `public_token` → returns `201` with accounts
5. `GET /connect/connections` → new connection appears with `status: linked` and `provider: plaid`
6. Celery ingestion task picks up the connection → transactions synced
7. `DELETE /connect/connections/{id}` → Plaid item revoked, connection set to revoked