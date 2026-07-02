import uuid
from datetime import date as date_type
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.transaction import TransactionStatus
from app.models.user import User
from app.schemas.transaction import (
    TransactionCreate,
    TransactionRead,
    TransactionUpdate,
)
from app.services import account_service, transaction_service

router = APIRouter()


@router.get("", response_model=list[TransactionRead])
async def list_transactions(
    account_id: Optional[uuid.UUID] = Query(None),
    category_id: Optional[uuid.UUID] = Query(None),
    date_from: Optional[date_type] = Query(None),
    date_to: Optional[date_type] = Query(None),
    search: Optional[str] = Query(None),
    status: Optional[TransactionStatus] = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List transactions with optional filters (FR-13)."""
    txns, _ = transaction_service.get_transactions(
        db,
        user_id=current_user.id,
        account_id=account_id,
        category_id=category_id,
        date_from=date_from,
        date_to=date_to,
        search=search,
        status=status,
        offset=offset,
        limit=limit,
    )
    return txns


@router.get("/{transaction_id}", response_model=TransactionRead)
async def get_transaction(
    transaction_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get a single transaction by ID."""
    try:
        return transaction_service.get_transaction(
            db, transaction_id=transaction_id, user_id=current_user.id
        )
    except transaction_service.TransactionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )


@router.patch("/{transaction_id}", response_model=TransactionRead)
async def update_transaction_category(
    transaction_id: uuid.UUID,
    payload: TransactionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Override the category of a transaction (FR-12)."""
    try:
        return transaction_service.update_transaction_category(
            db,
            transaction_id=transaction_id,
            user_id=current_user.id,
            category_id=payload.category_id,
            category_source=payload.category_source,
        )
    except transaction_service.TransactionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )


@router.post("", response_model=TransactionRead, status_code=status.HTTP_201_CREATED)
async def create_manual_transaction(
    payload: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a manual transaction (FR-14)."""
    try:
        return transaction_service.create_manual_transaction(
            db,
            account_id=payload.account_id,
            user_id=current_user.id,
            amount=payload.amount,
            currency=payload.currency,
            booking_date=payload.booking_date,
            description=payload.description,
            counterparty_name=payload.counterparty_name,
            category_id=payload.category_id,
        )
    except account_service.AccountNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )
