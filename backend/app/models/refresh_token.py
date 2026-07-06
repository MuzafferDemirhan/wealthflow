import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.db.base_class import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class RefreshToken(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A persisted, revocable refresh token (FR-02).

    We store a hash of the token rather than the raw value, and only
    ever compare hashes - mirroring how `hashed_password` is handled
    for users. Each refresh additionally rotates the token (old one
    revoked, new one issued) to limit the blast radius of a leaked
    token.
    """

    __tablename__ = "refresh_token"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("user_account.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<RefreshToken id={self.id} user_id={self.user_id} revoked={self.revoked}>"
