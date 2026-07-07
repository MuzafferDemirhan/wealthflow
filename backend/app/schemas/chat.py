import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class SendMessageRequest(BaseModel):
    message: str
    conversation_id: Optional[uuid.UUID] = None


class ChatMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str
    created_at: datetime


class ChatResponse(BaseModel):
    conversation_id: uuid.UUID
    reply: str
    message_id: uuid.UUID


class ChatHistoryParams(BaseModel):
    conversation_id: Optional[uuid.UUID] = None
    limit: int = 50
