import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, ForeignKey, Unicode
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.db.base_class import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.transaction import Transaction


class Category(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Transaction category taxonomy (FR - ML categorization, budgets).

    Two-level hierarchy via self-referential `parent_id` (e.g.
    "Food & Drink" -> "Groceries", "Restaurants"). `is_system` marks
    seeded categories the ML classifier's label set is trained
    against; those are not user-editable/deletable. `user_id` is
    null for system categories and set for a user's custom ones -
    custom categories are excluded from ML training data but can
    still be assigned manually and budgeted against.
    """

    __tablename__ = "category"

    name: Mapped[str] = mapped_column(Unicode(100), nullable=False)
    slug: Mapped[str] = mapped_column(Unicode(100), unique=True, nullable=False)
    icon: Mapped[Optional[str]] = mapped_column(Unicode(50), nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # NOTE: no ondelete=SET NULL here (deliberately). SQL Server
    # rejects a self-referencing FK with a cascading action on a
    # table that's already reachable via a cascading path from
    # another root (`user.id` -> `category.user_id` CASCADE, see
    # below) - combining the two triggers a "cycles or multiple
    # cascade paths" error at CREATE TABLE time. Deleting a parent
    # category with children must be handled in the service layer
    # (reparent or reject the delete) rather than at the DB level.
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("category.id"),
        nullable=True,
        index=True,
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    parent: Mapped[Optional["Category"]] = relationship(
        remote_side="Category.id",
        back_populates="children",
    )
    children: Mapped[list["Category"]] = relationship(
        back_populates="parent",
    )
    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="category",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Category id={self.id} slug={self.slug!r}>"
