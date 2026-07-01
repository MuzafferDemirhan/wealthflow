"""
Transaction persistence helpers shared by the ingestion pipeline.

Kept separate from `app/tasks/ingestion.py` so the dedupe-hash logic
(which the `transaction.dedupe_hash` unique constraint depends on)
is a plain, unit-testable function with no Celery or DB session in
the call path.
"""

import hashlib
import uuid
from datetime import date
from decimal import Decimal


def compute_dedupe_hash(
    *,
    account_id: uuid.UUID,
    amount: Decimal,
    currency: str,
    booking_date: date,
    description: str,
) -> str:
    """
    Deterministic idempotency key for a transaction within an account.

    Used as the actual dedup key (see `Transaction.dedupe_hash` and
    `uq_transaction_account_dedupe`) because the provider's own
    transaction ID is not guaranteed to be present or stable — Nordigen
    frequently omits `transactionId` for PENDING entries, and the same
    logical transaction can show up first as PENDING (no ID) and later
    as BOOKED (with an ID) after settlement.

    NOT collision-proof against two genuinely distinct transactions
    with identical amount/date/description on the same account (e.g.
    two separate €5 coffees on the same day with the same merchant
    string) — that's an accepted tradeoff for Sprint 2. If it proves
    to matter in practice, the ingestion pipeline can widen this with
    a same-day occurrence counter before hashing.
    """
    # Decimal is quantized to a fixed string form (not `str(amount)`
    # directly) so e.g. Decimal("10") and Decimal("10.00") — which can
    # arrive from different provider payload shapes for the same
    # underlying value — hash identically.
    normalized_amount = format(amount, ".4f")
    raw = "|".join(
        [
            str(account_id),
            normalized_amount,
            currency.upper(),
            booking_date.isoformat(),
            description.strip().lower(),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
