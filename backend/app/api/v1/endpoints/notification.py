import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.notification import Notification
from app.models.user import User
from app.schemas.notification import (
    MarkReadRequest,
    NotificationRead,
    NotificationUnreadCount,
)

router = APIRouter()


@router.get("", response_model=list[NotificationRead])
async def list_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List all notifications for the current user, newest first."""
    stmt = (
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
    )
    return list(db.execute(stmt).scalars().all())


@router.get("/unread-count", response_model=NotificationUnreadCount)
async def unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Return the count of unread notifications."""
    stmt = (
        select(Notification)
        .where(
            Notification.user_id == current_user.id,
            not Notification.is_read,
        )
    )
    count = len(list(db.execute(stmt).scalars().all()))
    return NotificationUnreadCount(count=count)


@router.patch("/mark-read", status_code=204)
async def mark_read(
    body: MarkReadRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Mark specific notifications as read."""
    stmt = (
        update(Notification)
        .where(
            Notification.id.in_(body.notification_ids),
            Notification.user_id == current_user.id,
        )
        .values(is_read=True)
    )
    db.execute(stmt)
    db.commit()
