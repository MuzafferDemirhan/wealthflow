import enum
import uuid
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base_class import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class ExportStatus(str, enum.Enum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ExportFormat(str, enum.Enum):
    PDF = "pdf"
    CSV = "csv"


class Export(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "export"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user_account.id"), nullable=False, index=True
    )
    format: Mapped[ExportFormat] = mapped_column(
        SAEnum(ExportFormat, name="export_format", native_enum=False, length=10),
        nullable=False,
    )
    report_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="category_breakdown, income_vs_expenses, monthly_trends, net_worth"
    )
    status: Mapped[ExportStatus] = mapped_column(
        SAEnum(ExportStatus, name="export_status", native_enum=False, length=20),
        default=ExportStatus.PROCESSING,
        nullable=False,
    )
    filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    params: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship(back_populates="exports")
