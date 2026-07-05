"""
Plaid provider adapter.

Auth flow:
  1. Backend creates a link_token  -> returned to frontend
  2. Frontend opens Plaid Link SDK -> user authenticates with their bank
  3. Frontend receives public_token -> POSTs it to our backend
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
from plaid.model.item_public_token_exchange_request import (
    ItemPublicTokenExchangeRequest,
)
from plaid.model.item_remove_request import ItemRemoveRequest
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
    host_map = {
        "sandbox": plaid.Environment.Sandbox,
        "development": plaid.Environment.Development if hasattr(plaid.Environment, "Development") else plaid.Environment.Sandbox,
        "production": plaid.Environment.Production,
    }
    plaid_env = host_map.get(env.lower(), plaid.Environment.Sandbox)
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
    # Token exchange (Step 2: public_token -> access_token)
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
                    iban=None,
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
        `{access_token}::{account_id}` - parsed internally.
        """
        if "::" in external_account_id:
            access_token, account_id = external_account_id.split("::", 1)
        else:
            raise PlaidProviderError(
                "PlaidAdapter.fetch_transactions requires 'access_token::account_id' format"
            )

        all_txns = self._sync_all_transactions(access_token)
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
        return Decimal("0"), None

    def create_requisition(
        self, institution_id: str, redirect_uri: str, reference: str
    ) -> dict:
        link_token = self.create_link_token(user_id=reference, redirect_uri=redirect_uri)
        return {
            "link_token": link_token,
            "url": None,
            "authorization_id": reference,
        }

    def get_requisition(self, requisition_id: str) -> dict:
        return {"status": "AUTHORIZED"}

    # ------------------------------------------------------------------
    # Revoke item
    # ------------------------------------------------------------------

    def revoke_item(self, access_token: str) -> None:
        """Remove the Plaid item, revoking access."""
        try:
            self._client.item_remove(ItemRemoveRequest(access_token=access_token))
        except plaid.ApiException as exc:
            raise PlaidProviderError(f"item/remove failed: {exc.body}") from exc

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _sync_all_transactions(self, access_token: str) -> list[ProviderTransaction]:
        """
        Use /transactions/sync (cursor-based, recommended by Plaid).
        Fetches all added transactions.
        """
        transactions: list[ProviderTransaction] = []
        cursor: Optional[str] = None

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
        # WealthFlow convention: negative = expense, positive = income - flip sign
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
