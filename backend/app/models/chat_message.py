import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.db.base_class import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class ChatMessage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A single message in a chat conversation with the AI advisor."""

    __tablename__ = "chat_message"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user_account.id"), nullable=False, index=True
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        index=True,
        default=uuid.uuid4,
    )
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="user or assistant"
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)

    user: Mapped["User"] = relationship(back_populates="chat_messages")
