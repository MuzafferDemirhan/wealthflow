import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.account import Account


class AccountNotFoundError(Exception):
    pass


def get_user_accounts(db: Session, *, user_id: uuid.UUID) -> list[Account]:
    stmt = (
        select(Account)
        .where(Account.user_id == user_id, Account.is_active)
        .order_by(Account.display_name)
    )
    return list(db.scalars(stmt).all())


def get_account(db: Session, *, account_id: uuid.UUID, user_id: uuid.UUID) -> Account:
    stmt = select(Account).where(
        Account.id == account_id, Account.user_id == user_id
    )
    account = db.scalar(stmt)
    if account is None:
        raise AccountNotFoundError()
    return account


def deactivate_account(db: Session, *, account_id: uuid.UUID, user_id: uuid.UUID) -> None:
    stmt = select(Account).where(
        Account.id == account_id, Account.user_id == user_id
    )
    account = db.scalar(stmt)
    if account is None:
        raise AccountNotFoundError()
    account.is_active = False
    db.add(account)
    db.commit()
