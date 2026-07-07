import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.chat import (
    ChatHistoryParams,
    ChatMessageRead,
    ChatResponse,
    SendMessageRequest,
)
from app.services import chat_service

router = APIRouter()


@router.post("/messages", response_model=ChatResponse)
async def send_message(
    body: SendMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    conversation_id = body.conversation_id or uuid.uuid4()
    assistant_msg = chat_service.process_message(
        db,
        user_id=current_user.id,
        message=body.message,
        conversation_id=conversation_id,
    )
    return ChatResponse(
        conversation_id=conversation_id,
        reply=assistant_msg.content,
        message_id=assistant_msg.id,
    )


@router.get("/messages", response_model=list[ChatMessageRead])
async def get_history(
    conversation_id: uuid.UUID,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return chat_service.get_history(
        db,
        user_id=current_user.id,
        conversation_id=conversation_id,
        limit=limit,
    )


@router.get("/conversations", response_model=list[uuid.UUID])
async def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return chat_service.get_conversations(db, user_id=current_user.id)


@router.delete("/messages/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    chat_service.delete_conversation(
        db, user_id=current_user.id, conversation_id=conversation_id
    )
