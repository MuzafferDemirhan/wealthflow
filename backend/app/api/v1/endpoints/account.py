import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.account import AccountRead
from app.services import account_service

router = APIRouter()


@router.get("", response_model=list[AccountRead])
async def list_accounts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List the authenticated user's active accounts with balances (FR-09)."""
    return account_service.get_user_accounts(db, user_id=current_user.id)


@router.get("/{account_id}", response_model=AccountRead)
async def get_account(
    account_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get a single account with its latest balance snapshot."""
    try:
        return account_service.get_account(
            db, account_id=account_id, user_id=current_user.id
        )
    except account_service.AccountNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_account(
    account_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Soft-delete (deactivate) a connected account (FR-10)."""
    try:
        account_service.deactivate_account(
            db, account_id=account_id, user_id=current_user.id
        )
    except account_service.AccountNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )


@router.post("/{account_id}/sync", status_code=status.HTTP_202_ACCEPTED)
async def sync_account(
    account_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Trigger a transaction sync for this account via Celery (FR-07)."""
    try:
        account_service.get_account(db, account_id=account_id, user_id=current_user.id)
    except account_service.AccountNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )
    from app.core.celery_app import celery_app
    celery_app.send_task(
        "ingestion.sync_account_transactions",
        args=[str(account_id)],
    )
    return {"message": "Sync triggered"}
