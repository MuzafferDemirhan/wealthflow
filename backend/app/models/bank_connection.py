import enum
import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Unicode
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.db.base_class import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.account import Account
    from app.models.user import User


class BankProvider(str, enum.Enum):
    """
    Open banking aggregator behind a connection. Only NORDIGEN is
    wired up in Sprint 2; the column exists as an enum (not hardcoded)
    so a second provider can be added later without a schema change —
    `app/services/providers/` follows the same abstraction.
    """

    NORDIGEN = "nordigen"


class ConnectionStatus(str, enum.Enum):
    """
    Our own simplified state machine, mapped from the provider's
    native status strings (Nordigen requisition status: CR, GC, UA,
    GA, LN, RJ, EX, SA, EX...) inside the provider adapter rather
    than leaking those codes into the domain model.
    """

    PENDING = "pending"  # requisition created, awaiting end-user bank auth
    LINKED = "linked"  # end-user completed auth, accounts available
    EXPIRED = "expired"  # consent window (typically 90 days) lapsed
    REVOKED = "revoked"  # end-user or bank revoked access
    ERROR = "error"  # provider-side failure creating/resolving the link


class BankConnection(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    One open-banking "link" session between a WealthFlow user and a
    financial institution via an aggregator (FR — Plaid/Nordigen
    integration). A single connection can yield multiple `Account`
    rows (a bank may expose several accounts under one consent).
    """

    __tablename__ = "bank_connection"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[BankProvider] = mapped_column(
        Enum(BankProvider, name="bank_provider", native_enum=False, length=20),
        nullable=False,
    )
    institution_id: Mapped[str] = mapped_column(Unicode(100), nullable=False)
    institution_name: Mapped[str] = mapped_column(Unicode(255), nullable=False)

    # Nordigen "requisition_id" — the handle used to poll status and
    # list accounts after the end-user completes the bank's auth flow.
    external_reference: Mapped[str] = mapped_column(
        Unicode(255), unique=True, nullable=False
    )
    status: Mapped[ConnectionStatus] = mapped_column(
        Enum(ConnectionStatus, name="connection_status", native_enum=False, length=20),
        default=ConnectionStatus.PENDING,
        nullable=False,
    )
    consent_expires_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped["User"] = relationship()
    accounts: Mapped[list["Account"]] = relationship(
        back_populates="bank_connection",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<BankConnection id={self.id} institution={self.institution_id!r} "
            f"status={self.status.value}>"
        )
