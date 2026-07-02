import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.transaction import CategorySource, TransactionStatus


class TransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    account_id: uuid.UUID
    category_id: Optional[uuid.UUID] = None
    external_id: Optional[str] = None
    dedupe_hash: str
    amount: Decimal
    currency: str
    booking_date: date
    value_date: Optional[date] = None
    status: TransactionStatus
    description: str
    counterparty_name: Optional[str] = None
    category_source: Optional[CategorySource] = None
    category_confidence: Optional[float] = None
    created_at: datetime
    updated_at: datetime


class TransactionUpdate(BaseModel):
    category_id: uuid.UUID
    category_source: CategorySource = CategorySource.USER


class TransactionCreate(BaseModel):
    account_id: uuid.UUID
    amount: Decimal = Field(..., decimal_places=4)
    currency: str = Field(min_length=3, max_length=3)
    booking_date: date
    description: str = Field(default="", max_length=500)
    counterparty_name: Optional[str] = Field(default=None, max_length=255)
    category_id: Optional[uuid.UUID] = None
