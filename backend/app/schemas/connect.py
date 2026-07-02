import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.bank_connection import ConnectionStatus


class InstitutionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    logo: Optional[str] = None
    country: str


class RequisitionCreate(BaseModel):
    institution_id: str = Field(..., min_length=1)
    redirect_uri: str = Field(..., min_length=1)


class RequisitionCreateResponse(BaseModel):
    id: uuid.UUID
    requisition_id: str
    link: str
    status: ConnectionStatus
    state: str


class AuthorizeRequest(BaseModel):
    code: str = Field(..., min_length=1)


class RequisitionRead(BaseModel):
    id: uuid.UUID
    requisition_id: str
    status: ConnectionStatus
    institution_id: str
    institution_name: str
    accounts_created: list[uuid.UUID] = []


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
