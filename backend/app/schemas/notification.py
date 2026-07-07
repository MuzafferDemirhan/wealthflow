import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: str
    title: str
    body: Optional[str] = None
    payload: Optional[dict[str, Any]] = None
    is_read: bool = False
    created_at: datetime


class NotificationUnreadCount(BaseModel):
    count: int


class MarkReadRequest(BaseModel):
    notification_ids: list[uuid.UUID]
