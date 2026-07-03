import enum
import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, Enum, Float, ForeignKey, Numeric, Unicode, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON, Uuid

from app.db.base_class import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.account import Account
    from app.models.category import Category


class TransactionStatus(str, enum.Enum):
    PENDING = "pending"  # booked provisionally, may still change/disappear
    BOOKED = "booked"


class CategorySource(str, enum.Enum):
    """
    Where `category_id` came from - lets the UI show a "suggested by
    AI, tap to confirm" affordance for ML-assigned categories, and
    lets the classifier's training pipeline pull only USER-confirmed
    (or RULE-confirmed) rows as ground truth, excluding its own
    unconfirmed guesses.
    """

    ML = "ml"
    RULE = "rule"
    USER = "user"


class Transaction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A single ledger entry ingested from a provider (FR - transaction
    ingestion pipeline, ML categorization, transactions endpoint).

    Idempotency: Nordigen does not guarantee a stable `transactionId`
    for every entry (notably PENDING ones), so ingestion cannot rely
    on `external_id` alone for dedup. `dedupe_hash` is a deterministic
    hash of (account_id, amount, currency, booking_date, description)
    computed by the ingestion pipeline and uniquely constrained per
    account - this is the actual dedup key; `external_id` is stored
    when available for provider-side lookups/debugging.
    """

    __tablename__ = "transaction"
    __table_args__ = (
        UniqueConstraint("account_id", "dedupe_hash", name="uq_transaction_account_dedupe"),
    )

    account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("account.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # NOTE: no ondelete=SET NULL here (deliberately) - `user` already
    # reaches `category` via CASCADE, and `category` would then
    # reach `transaction` via this FK's SET NULL, a second cascading
    # path into a table SQL Server already reaches through
    # `bank_connection` -> `account` -> `transaction` CASCADE.
    # The service layer must null out `category_id` on affected
    # transactions before a category can be deleted.
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("category.id"),
        nullable=True,
        index=True,
    )

    external_id: Mapped[Optional[str]] = mapped_column(Unicode(255), nullable=True, index=True)
    dedupe_hash: Mapped[str] = mapped_column(Unicode(64), nullable=False)

    # Signed amount: negative = money out, positive = money in - this
    # matches Nordigen's `transactionAmount.amount` convention, so the
    # provider adapter can pass it through without sign-flipping logic.
    amount: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    currency: Mapped[str] = mapped_column(Unicode(3), nullable=False)

    booking_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    value_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[TransactionStatus] = mapped_column(
        Enum(TransactionStatus, name="transaction_status", native_enum=False, length=20),
        default=TransactionStatus.BOOKED,
        nullable=False,
    )

    description: Mapped[str] = mapped_column(Unicode(500), nullable=False, default="")
    counterparty_name: Mapped[Optional[str]] = mapped_column(Unicode(255), nullable=True)

    category_source: Mapped[Optional[CategorySource]] = mapped_column(
        Enum(CategorySource, name="category_source", native_enum=False, length=10),
        nullable=True,
    )
    category_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Full provider payload for this entry, kept for debugging/
    # reprocessing (e.g. retraining the classifier off raw text
    # fields we don't currently map to a dedicated column).
    raw_payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    account: Mapped["Account"] = relationship(back_populates="transactions")
    category: Mapped[Optional["Category"]] = relationship(back_populates="transactions")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Transaction id={self.id} amount={self.amount} date={self.booking_date}>"
