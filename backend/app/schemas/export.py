import uuid
from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, field_validator


class ExportCreateRequest(BaseModel):
    report_type: str = "income_vs_expenses"
    format: str = "pdf"
    date_from: Optional[date] = None
    date_to: Optional[date] = None

    @field_validator("report_type")
    @classmethod
    def validate_report_type(cls, v: str) -> str:
        allowed = {
            "category_breakdown",
            "income_vs_expenses",
            "monthly_trends",
            "net_worth",
        }
        if v not in allowed:
            raise ValueError(f"report_type must be one of {allowed}")
        return v

    @field_validator("format")
    @classmethod
    def validate_format(cls, v: str) -> str:
        if v not in ("pdf", "csv"):
            raise ValueError("format must be 'pdf' or 'csv'")
        return v


class ExportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    format: str
    report_type: str
    status: str
    filename: Optional[str] = None
    params: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
