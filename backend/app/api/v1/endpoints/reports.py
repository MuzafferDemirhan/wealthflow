import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.report import (
    ReportCategoryBreakdown,
    ReportIncomeVsExpenses,
    ReportMonthlyTrends,
    ReportNetWorth,
)
from app.services import report_service

router = APIRouter()


@router.get("/category-breakdown", response_model=ReportCategoryBreakdown)
async def category_breakdown(
    date_from: date = Query(...),
    date_to: date = Query(...),
    account_id: Optional[uuid.UUID] = Query(None),
    currency: Optional[str] = Query(None, min_length=3, max_length=3),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Spending and income grouped by category for a date range."""
    return report_service.get_category_breakdown(
        db,
        user_id=current_user.id,
        date_from=date_from,
        date_to=date_to,
        account_id=account_id,
        currency=currency,
    )


@router.get("/income-vs-expenses", response_model=ReportIncomeVsExpenses)
async def income_vs_expenses(
    date_from: date = Query(...),
    date_to: date = Query(...),
    account_id: Optional[uuid.UUID] = Query(None),
    currency: Optional[str] = Query(None, min_length=3, max_length=3),
    monthly: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Income vs expenses summary with optional monthly breakdown."""
    return report_service.get_income_vs_expenses(
        db,
        user_id=current_user.id,
        date_from=date_from,
        date_to=date_to,
        account_id=account_id,
        currency=currency,
        monthly=monthly,
    )


@router.get("/monthly-trends", response_model=ReportMonthlyTrends)
async def monthly_trends(
    months: int = Query(12, ge=1, le=120),
    account_id: Optional[uuid.UUID] = Query(None),
    currency: Optional[str] = Query(None, min_length=3, max_length=3),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Monthly income/expense trends for the last N months."""
    return report_service.get_monthly_trends(
        db,
        user_id=current_user.id,
        months=months,
        account_id=account_id,
        currency=currency,
    )


@router.get("/net-worth", response_model=ReportNetWorth)
async def net_worth(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Net worth — total assets minus liabilities, with account type breakdown."""
    return report_service.get_net_worth(
        db,
        user_id=current_user.id,
    )
