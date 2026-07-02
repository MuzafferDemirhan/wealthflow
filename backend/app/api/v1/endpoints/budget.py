import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.budget import BudgetCreate, BudgetRead, BudgetUpdate
from app.services import budget_service

router = APIRouter()


@router.get("", response_model=list[BudgetRead])
async def list_budgets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List budgets with spending progress (FR-21, FR-22)."""
    return budget_service.get_user_budgets(db, user_id=current_user.id)


@router.post("", response_model=BudgetRead, status_code=status.HTTP_201_CREATED)
async def create_budget(
    payload: BudgetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a monthly budget per category (FR-21)."""
    try:
        return budget_service.create_budget(
            db,
            user_id=current_user.id,
            category_id=payload.category_id,
            period_month=payload.period_month,
            amount_limit=payload.amount_limit,
            currency=payload.currency,
        )
    except budget_service.BudgetConflictError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A budget for this category and month already exists",
        )


@router.put("/{budget_id}", response_model=BudgetRead)
async def update_budget(
    budget_id: uuid.UUID,
    payload: BudgetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update a budget's limit or category (FR-21)."""
    try:
        return budget_service.update_budget(
            db,
            budget_id=budget_id,
            user_id=current_user.id,
            amount_limit=payload.amount_limit,
            category_id=payload.category_id,
        )
    except budget_service.BudgetNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found",
        )


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_budget(
    budget_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Delete a budget (FR-21)."""
    try:
        budget_service.delete_budget(db, budget_id=budget_id, user_id=current_user.id)
    except budget_service.BudgetNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found",
        )
