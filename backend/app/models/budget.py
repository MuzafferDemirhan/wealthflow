import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, ForeignKey, Numeric, Unicode, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.db.base_class import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.user import User


class Budget(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A monthly spending limit (FR - budgets endpoint), optionally
    scoped to a category. `category_id = NULL` represents an overall
    "all spending" budget for that month.

    Granularity is a fixed calendar month (`period_month`, always the
    1st of the month) rather than a free-form date range - this is
    what the budgets endpoint and any progress/rollover calculation
    will key off of. Weekly/custom-period budgets are out of scope
    for Sprint 2; revisit if product requirements call for it.
    """

    __tablename__ = "budget"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "category_id", "period_month",
            name="uq_budget_user_category_period",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # NOTE: no ondelete=CASCADE here (deliberately) - `user` already
    # reaches `category` via CASCADE and `budget` directly via
    # CASCADE; adding a third cascading path users -> categories ->
    # budgets triggers SQL Server's "multiple cascade paths" error.
    # The service layer must delete/reassign budgets before a
    # category referenced by them can be deleted.
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("category.id"),
        nullable=True,
        index=True,
    )

    period_month: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    amount_limit: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    currency: Mapped[str] = mapped_column(Unicode(3), nullable=False)

    user: Mapped["User"] = relationship()
    category: Mapped[Optional["Category"]] = relationship()

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<Budget id={self.id} category_id={self.category_id} "
            f"period={self.period_month} limit={self.amount_limit}>"
        )
