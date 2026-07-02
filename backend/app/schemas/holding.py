import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.models.holding import AssetType


class HoldingCreate(BaseModel):
    symbol: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=255)
    asset_type: AssetType = AssetType.OTHER
    currency: str = Field(min_length=3, max_length=3)
    quantity: Decimal = Field(..., decimal_places=8)
    cost_basis: Optional[Decimal] = Field(default=None, decimal_places=4)
    current_price: Optional[Decimal] = Field(default=None, decimal_places=6)
    as_of_date: Optional[date] = None
    account_id: Optional[uuid.UUID] = None
    notes: Optional[str] = Field(default=None, max_length=1000)


class HoldingUpdate(BaseModel):
    symbol: Optional[str] = Field(default=None, min_length=1, max_length=20)
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    asset_type: Optional[AssetType] = None
    currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    quantity: Optional[Decimal] = Field(default=None, decimal_places=8)
    cost_basis: Optional[Decimal] = Field(default=None, decimal_places=4)
    current_price: Optional[Decimal] = Field(default=None, decimal_places=6)
    as_of_date: Optional[date] = None
    account_id: Optional[uuid.UUID] = None
    notes: Optional[str] = Field(default=None, max_length=1000)


class HoldingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    account_id: Optional[uuid.UUID] = None
    symbol: str
    name: str
    asset_type: AssetType
    currency: str
    quantity: Decimal
    cost_basis: Optional[Decimal] = None
    current_price: Optional[Decimal] = None
    as_of_date: Optional[date] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def market_value(self) -> Optional[Decimal]:
        if self.current_price is not None:
            return self.quantity * self.current_price
        return None


class PortfolioSummary(BaseModel):
    total_market_value: Decimal = Decimal("0")
    total_cost_basis: Optional[Decimal] = None
    total_gain_loss: Optional[Decimal] = None
    total_gain_loss_pct: Optional[float] = None
    holdings_count: int = 0
    allocation: dict[str, Decimal] = {}
