import enum
import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, Enum, ForeignKey, Numeric, Unicode
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.db.base_class import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.account import Account
    from app.models.user import User


class AssetType(str, enum.Enum):
    STOCK = "stock"
    ETF = "etf"
    MUTUAL_FUND = "mutual_fund"
    BOND = "bond"
    CRYPTO = "crypto"
    CASH = "cash"
    OTHER = "other"


class Holding(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "holding"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("account.id"),
        nullable=True,
        index=True,
    )

    symbol: Mapped[str] = mapped_column(Unicode(20), nullable=False, index=True)
    name: Mapped[str] = mapped_column(Unicode(255), nullable=False)
    asset_type: Mapped[AssetType] = mapped_column(
        Enum(AssetType, name="asset_type", native_enum=False, length=20),
        default=AssetType.OTHER,
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(Unicode(3), nullable=False)

    quantity: Mapped[Decimal] = mapped_column(Numeric(19, 8), nullable=False)
    cost_basis: Mapped[Optional[Decimal]] = mapped_column(Numeric(19, 4), nullable=True)
    current_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(19, 6), nullable=True)
    as_of_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    notes: Mapped[Optional[str]] = mapped_column(Unicode(1000), nullable=True)

    user: Mapped["User"] = relationship()
    account: Mapped[Optional["Account"]] = relationship()

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Holding id={self.id} symbol={self.symbol!r} qty={self.quantity}>"
