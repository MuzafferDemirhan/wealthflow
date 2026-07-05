import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.bank_connection import ConnectionStatus


# ── Plaid schemas ──────────────────────────────────────────────


class PlaidLinkTokenRequest(BaseModel):
    redirect_uri: Optional[str] = None


class PlaidLinkTokenResponse(BaseModel):
    link_token: str


class PlaidExchangeRequest(BaseModel):
    public_token: str = Field(..., min_length=1)
    institution_id: str = Field(..., min_length=1)
    institution_name: str = Field(..., min_length=1)


class PlaidExchangeResponse(BaseModel):
    id: uuid.UUID
    status: str
    institution_id: str
    institution_name: str
    accounts_created: list[uuid.UUID]
    item_id: str


class ConnectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    provider: str
    institution_id: str
    institution_name: str
    external_reference: str
    status: ConnectionStatus
    consent_expires_at: Optional[date] = None
    last_synced_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
