"""
Transaction persistence helpers shared by the ingestion pipeline and
the transactions REST endpoint.

Kept separate from `app/tasks/ingestion.py` so the dedupe-hash logic
(which the `transaction.dedupe_hash` unique constraint depends on)
is a plain, unit-testable function with no Celery or DB session in
the call path.
"""

import hashlib
import uuid
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.transaction import CategorySource, Transaction, TransactionStatus


def compute_dedupe_hash(
    *,
    account_id: uuid.UUID,
    amount: Decimal,
    currency: str,
    booking_date: date,
    description: str,
) -> str:
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


class TransactionNotFoundError(Exception):
    pass


def get_transactions(
    db: Session,
    *,
    user_id: uuid.UUID,
    account_id: Optional[uuid.UUID] = None,
    category_id: Optional[uuid.UUID] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    search: Optional[str] = None,
    status: Optional[TransactionStatus] = None,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[Transaction], int]:
    from app.models.account import Account

    base = select(Transaction).join(Account, Transaction.account_id == Account.id).where(
        Account.user_id == user_id, Account.is_active
    )

    count_base = (
        select(func.count(Transaction.id))
        .join(Account, Transaction.account_id == Account.id)
        .where(Account.user_id == user_id, Account.is_active)
    )

    if account_id is not None:
        base = base.where(Transaction.account_id == account_id)
        count_base = count_base.where(Transaction.account_id == account_id)
    if category_id is not None:
        base = base.where(Transaction.category_id == category_id)
        count_base = count_base.where(Transaction.category_id == category_id)
    if date_from is not None:
        base = base.where(Transaction.booking_date >= date_from)
        count_base = count_base.where(Transaction.booking_date >= date_from)
    if date_to is not None:
        base = base.where(Transaction.booking_date <= date_to)
        count_base = count_base.where(Transaction.booking_date <= date_to)
    if search:
        pattern = f"%{search}%"
        base = base.where(Transaction.description.ilike(pattern))
        count_base = count_base.where(Transaction.description.ilike(pattern))
    if status is not None:
        base = base.where(Transaction.status == status)
        count_base = count_base.where(Transaction.status == status)

    total = db.scalar(count_base) or 0

    stmt = base.order_by(Transaction.booking_date.desc(), Transaction.created_at.desc())
    if limit > 0:
        stmt = stmt.offset(offset).limit(limit)
    transactions = list(db.scalars(stmt).all())

    return transactions, total


def get_transaction(
    db: Session, *, transaction_id: uuid.UUID, user_id: uuid.UUID
) -> Transaction:
    from app.models.account import Account

    stmt = (
        select(Transaction)
        .join(Account, Transaction.account_id == Account.id)
        .where(Transaction.id == transaction_id, Account.user_id == user_id)
    )
    txn = db.scalar(stmt)
    if txn is None:
        raise TransactionNotFoundError()
    return txn


def update_transaction_category(
    db: Session,
    *,
    transaction_id: uuid.UUID,
    user_id: uuid.UUID,
    category_id: uuid.UUID,
    category_source: CategorySource = CategorySource.USER,
) -> Transaction:
    txn = get_transaction(db, transaction_id=transaction_id, user_id=user_id)
    txn.category_id = category_id
    txn.category_source = category_source
    txn.category_confidence = 1.0 if category_source == CategorySource.USER else None
    db.add(txn)
    db.commit()
    db.refresh(txn)
    return txn


def create_manual_transaction(
    db: Session,
    *,
    account_id: uuid.UUID,
    user_id: uuid.UUID,
    amount: Decimal,
    currency: str,
    booking_date: date,
    description: str,
    counterparty_name: Optional[str] = None,
    category_id: Optional[uuid.UUID] = None,
) -> Transaction:
    from app.models.account import Account

    account = db.scalar(
        select(Account).where(
            Account.id == account_id, Account.user_id == user_id, Account.is_active
        )
    )
    if account is None:
        from app.services.account_service import AccountNotFoundError
        raise AccountNotFoundError()

    txn = Transaction(
        account_id=account_id,
        external_id=None,
        dedupe_hash=compute_dedupe_hash(
            account_id=account_id,
            amount=amount,
            currency=currency,
            booking_date=booking_date,
            description=description,
        ),
        amount=amount,
        currency=currency.upper(),
        booking_date=booking_date,
        description=description,
        counterparty_name=counterparty_name,
        category_id=category_id,
        category_source=CategorySource.USER if category_id else None,
        status=TransactionStatus.BOOKED,
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)
    return txn
