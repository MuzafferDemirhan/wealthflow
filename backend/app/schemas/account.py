import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.account import AccountType


class AccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    bank_connection_id: uuid.UUID
    external_account_id: str
    display_name: str
    account_type: AccountType
    iban: Optional[str] = None
    currency: str
    current_balance: Decimal
    balance_as_of: Optional[datetime] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
