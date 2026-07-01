import uuid
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.budget import Budget
from app.models.transaction import Transaction


class BudgetNotFoundError(Exception):
    pass


class BudgetConflictError(Exception):
    pass


def _compute_spending(
    db: Session, *, user_id: uuid.UUID, category_id: Optional[uuid.UUID], period_month: date
) -> Decimal:
    next_month = (
        date(year=period_month.year + (period_month.month // 12), month=(period_month.month % 12) + 1, day=1)
        if period_month.month < 12
        else date(year=period_month.year + 1, month=1, day=1)
    )

    stmt = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
        Transaction.booking_date >= period_month,
        Transaction.booking_date < next_month,
    )

    if category_id is not None:
        stmt = stmt.where(Transaction.category_id == category_id)

    result = db.scalar(stmt)
    return Decimal(str(result)) if result is not None else Decimal("0")


def _get_next_month_start(year: int, month: int) -> date:
    if month == 12:
        return date(year + 1, 1, 1)
    return date(year, month + 1, 1)


def get_user_budgets(db: Session, *, user_id: uuid.UUID) -> list[dict]:
    budgets = (
        db.scalars(
            select(Budget)
            .where(Budget.user_id == user_id)
            .order_by(Budget.period_month.desc(), Budget.category_id.asc())
        )
        .all()
    )

    results = []
    for budget in budgets:
        spent = abs(
            _compute_spending(
                db, user_id=user_id, category_id=budget.category_id, period_month=budget.period_month
            )
        )
        remaining = budget.amount_limit - spent
        progress_pct = (
            float(spent / budget.amount_limit * 100) if budget.amount_limit > 0 else 0.0
        )
        results.append(
            {
                "id": budget.id,
                "user_id": budget.user_id,
                "category_id": budget.category_id,
                "period_month": budget.period_month,
                "amount_limit": budget.amount_limit,
                "currency": budget.currency,
                "created_at": budget.created_at,
                "updated_at": budget.updated_at,
                "spent": spent,
                "remaining": remaining,
                "progress_pct": progress_pct,
            }
        )
    return results


def create_budget(
    db: Session,
    *,
    user_id: uuid.UUID,
    category_id: Optional[uuid.UUID],
    period_month: date,
    amount_limit: Decimal,
    currency: str,
) -> Budget:
    existing = db.scalar(
        select(Budget).where(
            Budget.user_id == user_id,
            Budget.category_id == category_id,
            Budget.period_month == period_month,
        )
    )
    if existing is not None:
        raise BudgetConflictError()

    budget = Budget(
        user_id=user_id,
        category_id=category_id,
        period_month=period_month,
        amount_limit=amount_limit,
        currency=currency,
    )
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return budget


def update_budget(
    db: Session,
    *,
    budget_id: uuid.UUID,
    user_id: uuid.UUID,
    amount_limit: Optional[Decimal] = None,
    category_id: Optional[uuid.UUID] = None,
) -> Budget:
    stmt = select(Budget).where(Budget.id == budget_id, Budget.user_id == user_id)
    budget = db.scalar(stmt)
    if budget is None:
        raise BudgetNotFoundError()

    if amount_limit is not None:
        budget.amount_limit = amount_limit
    if category_id is not None:
        budget.category_id = category_id

    db.add(budget)
    db.commit()
    db.refresh(budget)
    return budget


def delete_budget(db: Session, *, budget_id: uuid.UUID, user_id: uuid.UUID) -> None:
    stmt = select(Budget).where(Budget.id == budget_id, Budget.user_id == user_id)
    budget = db.scalar(stmt)
    if budget is None:
        raise BudgetNotFoundError()
    db.delete(budget)
    db.commit()
