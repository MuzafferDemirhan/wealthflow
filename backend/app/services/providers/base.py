from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Optional


@dataclass
class ProviderAccount:
    external_account_id: str
    iban: Optional[str]
    currency: str
    display_name: str
    account_type: str
    current_balance: Decimal
    balance_as_of: Optional[datetime]


@dataclass
class ProviderTransaction:
    external_id: Optional[str]
    amount: Decimal
    currency: str
    booking_date: date
    value_date: Optional[date]
    status: str
    description: str
    counterparty_name: Optional[str]
    raw_payload: dict = field(default_factory=dict)


class ProviderAdapter(ABC):
    """Interface that every Open Banking provider adapter must implement.

    The ingestion pipeline and the account-connect flow depend on this
    interface, not on any concrete provider class, so a second
    aggregator (e.g. Plaid) can be added later without touching the
    pipeline code.
    """

    @abstractmethod
    def authenticate(self) -> str:
        """Obtain and return an access token for subsequent API calls."""

    @abstractmethod
    def fetch_accounts(self, requisition_id: str) -> list[ProviderAccount]:
        """Return all accounts associated with a given requisition/link session."""

    @abstractmethod
    def fetch_transactions(
        self, external_account_id: str, since: date
    ) -> list[ProviderTransaction]:
        """Return transactions for an account since the given date."""

    @abstractmethod
    def fetch_balances(self, external_account_id: str) -> tuple[Decimal, Optional[datetime]]:
        """Return (current_balance, balance_as_of) for an account."""

    @abstractmethod
    def create_requisition(
        self, institution_id: str, redirect_uri: str, reference: str
    ) -> dict:
        """Initiate a link session and return dict with 'id' and 'link' URL."""

    @abstractmethod
    def get_requisition(self, requisition_id: str) -> dict:
        """Return the full requisition object including its status and account list."""
