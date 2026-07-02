import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class BudgetCreate(BaseModel):
    category_id: Optional[uuid.UUID] = None
    period_month: date
    amount_limit: Decimal = Field(..., decimal_places=4)
    currency: str = Field(min_length=3, max_length=3)


class BudgetUpdate(BaseModel):
    amount_limit: Optional[Decimal] = Field(default=None, decimal_places=4)
    category_id: Optional[uuid.UUID] = None


class BudgetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    category_id: Optional[uuid.UUID] = None
    period_month: date
    amount_limit: Decimal
    currency: str
    created_at: datetime
    updated_at: datetime
    spent: Decimal = Decimal("0")
    remaining: Decimal = Decimal("0")
    progress_pct: float = 0.0
