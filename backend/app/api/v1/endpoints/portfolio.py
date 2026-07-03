import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.holding import (
    HoldingCreate,
    HoldingRead,
    HoldingUpdate,
    PortfolioSummary,
)
from app.services import portfolio_service

router = APIRouter()


@router.get("/holdings", response_model=list[HoldingRead])
async def list_holdings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List all investment holdings for the current user."""
    return portfolio_service.get_user_holdings(db, user_id=current_user.id)


@router.post("/holdings", response_model=HoldingRead, status_code=status.HTTP_201_CREATED)
async def create_holding(
    payload: HoldingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Add a new investment holding to the portfolio."""
    return portfolio_service.create_holding(
        db,
        user_id=current_user.id,
        symbol=payload.symbol,
        name=payload.name,
        asset_type=payload.asset_type,
        currency=payload.currency,
        quantity=payload.quantity,
        cost_basis=payload.cost_basis,
        current_price=payload.current_price,
        as_of_date=payload.as_of_date,
        account_id=payload.account_id,
        notes=payload.notes,
    )


@router.get("/holdings/{holding_id}", response_model=HoldingRead)
async def get_holding(
    holding_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get a single holding by ID."""
    try:
        return portfolio_service.get_holding(
            db, holding_id=holding_id, user_id=current_user.id
        )
    except portfolio_service.HoldingNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Holding not found",
        )


@router.put("/holdings/{holding_id}", response_model=HoldingRead)
async def update_holding(
    holding_id: uuid.UUID,
    payload: HoldingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update an existing holding (partial update)."""
    try:
        return portfolio_service.update_holding(
            db,
            holding_id=holding_id,
            user_id=current_user.id,
            symbol=payload.symbol,
            name=payload.name,
            asset_type=payload.asset_type,
            currency=payload.currency,
            quantity=payload.quantity,
            cost_basis=payload.cost_basis,
            current_price=payload.current_price,
            as_of_date=payload.as_of_date,
            account_id=payload.account_id,
            notes=payload.notes,
        )
    except portfolio_service.HoldingNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Holding not found",
        )


@router.delete("/holdings/{holding_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_holding(
    holding_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Delete a holding from the portfolio."""
    try:
        portfolio_service.delete_holding(db, holding_id=holding_id, user_id=current_user.id)
    except portfolio_service.HoldingNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Holding not found",
        )


@router.get("/summary", response_model=PortfolioSummary)
async def portfolio_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Aggregate portfolio summary - total value, cost basis, gain/loss, allocation."""
    return portfolio_service.compute_summary(db, user_id=current_user.id)
