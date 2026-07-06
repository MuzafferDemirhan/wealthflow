"""
Transaction ingestion pipeline (Celery tasks).
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.encryption import decrypt_token
from app.db.session import SessionLocal
from app.models.account import Account
from app.models.bank_connection import BankConnection, ConnectionStatus
from app.models.transaction import Transaction, TransactionStatus
from app.services.providers.base import ProviderTransaction
from app.services.providers.plaid import PlaidAdapter, PlaidProviderError
from app.services.transaction_service import compute_dedupe_hash

_INITIAL_LOOKBACK_DAYS = 90
_STALE_AFTER_HOURS = 4


@celery_app.task(name="ingestion.sync_account_transactions", bind=True, max_retries=3)
def sync_account_transactions(self, account_id: str) -> dict:
    db = SessionLocal()
    try:
        parsed_id = uuid.UUID(account_id)
    except ValueError:
        return {"ok": False, "error": f"invalid account_id: {account_id}"}

    try:
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

        try:
            provider, access_token = _build_adapter_for_connection(conn)
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}

        since = _compute_since(conn.last_synced_at)

        try:
            encoded_id = f"{access_token}::{account.external_account_id}"
            raw_txns = provider.fetch_transactions(encoded_id, since)
        except PlaidProviderError as exc:
            raise self.retry(exc=exc)

        new_ids: list[str] = []
        for raw in raw_txns:
            txn_id = _upsert_transaction(db, account_id=parsed_id, raw=raw)
            if txn_id is not None:
                new_ids.append(str(txn_id))

        try:
            balance, balance_as_of = provider.fetch_balances(f"{access_token}::{account.external_account_id}")
            account.current_balance = balance
            account.balance_as_of = balance_as_of
        except PlaidProviderError:
            pass

        conn.last_synced_at = datetime.now(timezone.utc)
        db.add(account)
        db.add(conn)
        db.commit()

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


@celery_app.task(name="ingestion.sync_all_due_connections")
def sync_all_due_connections() -> dict:
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


def _build_adapter_for_connection(conn: BankConnection):
    return (
        PlaidAdapter(
            client_id=settings.PLAID_CLIENT_ID,
            secret=settings.PLAID_SECRET,
            env=settings.PLAID_ENV,
        ),
        decrypt_token(conn.external_reference),
    )


def _compute_since(last_synced_at: Optional[datetime]) -> date:
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
    dedupe = compute_dedupe_hash(
        account_id=account_id,
        amount=raw.amount,
        currency=raw.currency,
        booking_date=raw.booking_date,
        description=raw.description,
    )

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
