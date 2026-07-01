"""
Transaction ingestion pipeline (Celery tasks).

Pipeline shape (target, once the Nordigen client lands):

    sync_all_due_connections()            [periodic, e.g. every 4h via celery beat]
        -> finds BankConnection rows with status=LINKED whose
           last_synced_at is stale
        -> fan-out: sync_account_transactions.delay(account_id) per account

    sync_account_transactions(account_id)  [per-account task]
        -> provider.fetch_transactions(external_account_id, since=...)
        -> for each raw transaction:
             - compute_dedupe_hash(...)
             - upsert Transaction (insert if new, on conflict do
               nothing — dedupe_hash is the idempotency key, so a
               transaction already stored, PENDING or BOOKED, is
               never duplicated by a re-sync)
        -> refresh Account.current_balance / balance_as_of
        -> enqueue classify_transaction.delay(transaction_id) for any
           newly-inserted, uncategorized rows (Sprint 2 ML classifier)

This module currently only wires up the task registration and DB
session handling so `celery -A app.core.celery_app worker` starts
cleanly; the provider call and upsert logic are intentionally left as
NotImplementedError until the Nordigen adapter (`app/services/
providers/nordigen.py`) exists — filling that in is the next step.
"""

import uuid

from app.core.celery_app import celery_app
from app.db.session import SessionLocal


@celery_app.task(name="ingestion.sync_account_transactions", bind=True, max_retries=3)
def sync_account_transactions(self, account_id: str) -> None:
    """Fetch and persist new transactions for a single linked account."""
    db = SessionLocal()
    try:
        _ = uuid.UUID(account_id)  # fail fast on a malformed task payload
        # TODO(Sprint 2 — Nordigen step):
        #   1. Load Account + parent BankConnection from `db`.
        #   2. Call the Nordigen provider adapter to fetch raw transactions.
        #   3. For each: compute_dedupe_hash(...), upsert via `db`.
        #   4. Update Account.current_balance / balance_as_of.
        #   5. celery_app.send_task("ingestion.classify_transaction", ...)
        #      for newly-inserted rows.
        raise NotImplementedError(
            "Nordigen provider adapter not yet wired up — see module docstring."
        )
    finally:
        db.close()


@celery_app.task(name="ingestion.sync_all_due_connections")
def sync_all_due_connections() -> None:
    """Periodic fan-out: find stale LINKED connections, enqueue per-account syncs."""
    db = SessionLocal()
    try:
        # TODO(Sprint 2 — Nordigen step): query BankConnection where
        # status == LINKED and (last_synced_at is null or stale),
        # then sync_account_transactions.delay(str(account.id)) for
        # each of that connection's accounts.
        raise NotImplementedError(
            "Nordigen provider adapter not yet wired up — see module docstring."
        )
    finally:
        db.close()
