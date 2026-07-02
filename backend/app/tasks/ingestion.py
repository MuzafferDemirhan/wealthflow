"""
Transaction ingestion pipeline (Celery tasks).

Pipeline shape::

    sync_all_due_connections()            [periodic via celery beat, e.g. every 4h]
        -> finds BankConnection rows with status=LINKED whose
           last_synced_at is stale
        -> fan-out: sync_account_transactions.delay(account_id) per account

    sync_account_transactions(account_id)  [per-account task]
        -> provider.fetch_transactions(external_account_id, since=...)
        -> for each raw transaction:
             - compute dedupe_hash
             - upsert Transaction (skip if dedupe_hash already exists)
        -> refresh Account.current_balance / balance_as_of
        -> enqueue classify_transaction.delay(txn_id) for any
           newly-inserted, uncategorized rows
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.core.celery_app import celery_app
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.account import Account
from app.models.bank_connection import BankConnection, ConnectionStatus
from app.models.transaction import Transaction, TransactionStatus
from app.services.providers.base import ProviderTransaction
from app.services.providers.nordigen import NordigenAdapter, ProviderError
from app.services.transaction_service import compute_dedupe_hash

# Default lookback window for first sync (calendar days)
_INITIAL_LOOKBACK_DAYS = 90

# How recently a "due" connection must have been synced to skip
_STALE_AFTER_HOURS = 4


# ------------------------------------------------------------------
# Per-account sync
# ------------------------------------------------------------------


@celery_app.task(name="ingestion.sync_account_transactions", bind=True, max_retries=3)
def sync_account_transactions(self, account_id: str) -> dict:
    """Fetch and persist new transactions for a single linked account."""
    db = SessionLocal()
    try:
        parsed_id = uuid.UUID(account_id)
    except ValueError:
        return {"ok": False, "error": f"invalid account_id: {account_id}"}

    try:
        # 1. Load Account + parent BankConnection (eagerly)
        stmt = (
            select(Account)
            .options(joinedload(Account.bank_connection))
            .where(Account.id == parsed_id, Account.is_active)
        )
        account = db.scalar(stmt)
        if account is None:
            return {"ok": False, "error": "account not found or inactive"}
        conn: BankConnection = account.bank_connection
        if conn.status != ConnectionStatus.LINKED:
            return {"ok": False, "error": f"connection status is {conn.status.value}, not LINKED"}

        # 2. Build the provider adapter
        if conn.provider.value != "nordigen":
            return {"ok": False, "error": f"unsupported provider: {conn.provider.value}"}

        provider = _build_provider()

        # 3. Determine date range
        since = _compute_since(conn.last_synced_at)

        # 4. Fetch raw transactions from the provider
        try:
            raw_txns = provider.fetch_transactions(account.external_account_id, since)
        except ProviderError as exc:
            raise self.retry(exc=exc)

        # 5. Upsert transactions
        new_ids: list[str] = []
        for raw in raw_txns:
            txn_id = _upsert_transaction(db, account_id=parsed_id, raw=raw)
            if txn_id is not None:
                new_ids.append(str(txn_id))

        # 6. Refresh balance from provider
        try:
            balance, balance_as_of = provider.fetch_balances(account.external_account_id)
            account.current_balance = balance
            account.balance_as_of = balance_as_of
        except ProviderError:
            pass  # non-fatal — balances will be retried on next sync

        # 7. Update last_synced_at
        conn.last_synced_at = datetime.now(timezone.utc)
        db.add(account)
        db.add(conn)
        db.commit()

        # 8. Enqueue classification for newly-inserted uncategorized transactions
        for txn_id_str in new_ids:
            celery_app.send_task("ingestion.classify_transaction", args=[txn_id_str])

        return {
            "ok": True,
            "account_id": account_id,
            "transactions_fetched": len(raw_txns),
            "transactions_new": len(new_ids),
        }

    except Exception as exc:
        db.rollback()
        raise self.retry(exc=exc)
    finally:
        db.close()


# ------------------------------------------------------------------
# Fan-out: sync all due connections
# ------------------------------------------------------------------


@celery_app.task(name="ingestion.sync_all_due_connections")
def sync_all_due_connections() -> dict:
    """Periodic fan-out: find stale LINKED connections, enqueue per-account syncs."""
    db = SessionLocal()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=_STALE_AFTER_HOURS)

        stmt = (
            select(BankConnection)
            .options(joinedload(BankConnection.accounts))
            .where(
                BankConnection.status == ConnectionStatus.LINKED,
                (BankConnection.last_synced_at.is_(None))
                | (BankConnection.last_synced_at < cutoff),
            )
        )
        connections = list(db.scalars(stmt).unique().all())

        enqueued = 0
        for conn in connections:
            for account in conn.accounts:
                if account.is_active:
                    sync_account_transactions.delay(str(account.id))
                    enqueued += 1

        return {
            "ok": True,
            "connections_found": len(connections),
            "accounts_enqueued": enqueued,
        }
    finally:
        db.close()


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _build_provider() -> NordigenAdapter:
    return NordigenAdapter(
        secret_id=settings.NORDIGEN_SECRET_ID,
        secret_key=settings.NORDIGEN_SECRET_KEY,
    )


def _compute_since(last_synced_at: Optional[datetime]) -> date:
    """Earliest date for which to fetch transactions.

    - If the connection has been synced before: 90 days before that
      sync or 90 days ago, whichever is *earlier* — guarantees no gap.
    - If never synced: 90 days ago from today.
    """
    now = date.today()
    earliest = now - timedelta(days=_INITIAL_LOOKBACK_DAYS)
    if last_synced_at is not None:
        from_last_sync = last_synced_at.date() - timedelta(days=_INITIAL_LOOKBACK_DAYS)
        return min(earliest, from_last_sync)
    return earliest


def _upsert_transaction(
    db: SessionLocal,
    *,
    account_id: uuid.UUID,
    raw: "ProviderTransaction",
) -> Optional[uuid.UUID]:
    """Insert a new transaction if its dedupe_hash is not yet stored.

    Returns the new transaction's UUID, or ``None`` if it was a
    duplicate (already existed).
    """
    dedupe = compute_dedupe_hash(
        account_id=account_id,
        amount=raw.amount,
        currency=raw.currency,
        booking_date=raw.booking_date,
        description=raw.description,
    )

    # Check for existing
    existing = db.scalar(
        select(Transaction.id).where(
            Transaction.account_id == account_id,
            Transaction.dedupe_hash == dedupe,
        )
    )
    if existing is not None:
        return None

    txn_id = uuid.uuid4()
    txn_status = TransactionStatus.PENDING if raw.status == "pending" else TransactionStatus.BOOKED

    txn = Transaction(
        id=txn_id,
        account_id=account_id,
        external_id=raw.external_id,
        dedupe_hash=dedupe,
        amount=raw.amount,
        currency=raw.currency.upper(),
        booking_date=raw.booking_date,
        value_date=raw.value_date,
        status=txn_status,
        description=raw.description,
        counterparty_name=raw.counterparty_name,
        raw_payload=raw.raw_payload,
    )
    db.add(txn)
    db.flush()
    return txn_id
