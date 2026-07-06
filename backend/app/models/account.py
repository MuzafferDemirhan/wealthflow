import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Numeric, Unicode
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.db.base_class import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.bank_connection import BankConnection
    from app.models.transaction import Transaction
    from app.models.user import User


class AccountType(str, enum.Enum):
    """
    Our normalized account type. Mapped from Nordigen's `cashAccountType`
    (ISO 20022 ExternalCashAccountType1Code, e.g. CACC/SVGS/CARD) inside
    the provider adapter - raw codes never reach the domain layer.
    """

    CHECKING = "checking"
    SAVINGS = "savings"
    CREDIT_CARD = "credit_card"
    LOAN = "loan"
    INVESTMENT = "investment"
    OTHER = "other"


class Account(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A single bank account linked via a `BankConnection` (FR - accounts
    endpoint, transaction ingestion target). `user_id` is denormalized
    from the parent connection so account-scoped queries (list my
    accounts, list transactions for account X owned by user Y) don't
    need a join through `bank_connection` on every request.
    """

    __tablename__ = "account"

    # NOTE: no ondelete=CASCADE here (deliberately). SQL Server refuses
    # to create a schema where a table is reachable via more than one
    # cascading path from the same root - and `user` already reaches
    # this table via `bank_connection.user_id` CASCADE ->
    # `account.bank_connection_id` CASCADE. This FK exists for
    # query convenience (denormalized owner), not as a cleanup path.
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("user_account.id"),
        nullable=False,
        index=True,
    )
    bank_connection_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("bank_connection.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Nordigen account UUID - stable identifier used to fetch
    # balances/transactions for this account from the provider.
    external_account_id: Mapped[str] = mapped_column(
        Unicode(255), unique=True, nullable=False
    )

    display_name: Mapped[str] = mapped_column(Unicode(255), nullable=False)
    account_type: Mapped[AccountType] = mapped_column(
        Enum(AccountType, name="account_type", native_enum=False, length=20),
        default=AccountType.OTHER,
        nullable=False,
    )
    iban: Mapped[Optional[str]] = mapped_column(Unicode(34), nullable=True)
    currency: Mapped[str] = mapped_column(Unicode(3), nullable=False)

    # Last known balance snapshot, refreshed on each sync - kept
    # denormalized here for cheap "account list with balances" reads
    # without aggregating transactions on every request.
    current_balance: Mapped[Decimal] = mapped_column(
        Numeric(19, 4), default=Decimal("0"), nullable=False
    )
    balance_as_of: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped["User"] = relationship()
    bank_connection: Mapped["BankConnection"] = relationship(back_populates="accounts")
    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="account",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Account id={self.id} name={self.display_name!r} currency={self.currency}>"
