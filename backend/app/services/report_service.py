import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.account import Account, AccountType
from app.models.holding import Holding
from app.models.transaction import Transaction, TransactionStatus

# ------------------------------------------------------------------
# Category breakdown
# ------------------------------------------------------------------


def _categorise_amount(amount: Decimal) -> tuple[Decimal, Decimal]:
    """Split a signed amount into (income, expense).

    Income is stored as positive amounts, expenses as negative.
    We report absolute values for the expense side.
    """
    if amount >= 0:
        return (amount, Decimal("0"))
    return (Decimal("0"), abs(amount))


def get_category_breakdown(
    db: Session,
    *,
    user_id: uuid.UUID,
    date_from: date,
    date_to: date,
    account_id: Optional[uuid.UUID] = None,
    currency: Optional[str] = None,
) -> dict:
    stmt = (
        select(Transaction)
        .join(Account, Transaction.account_id == Account.id)
        .options(joinedload(Transaction.category))
        .where(
            Account.user_id == user_id,
            Account.is_active,
            Transaction.status == TransactionStatus.BOOKED,
            Transaction.booking_date >= date_from,
            Transaction.booking_date <= date_to,
        )
    )
    if account_id is not None:
        stmt = stmt.where(Transaction.account_id == account_id)
    if currency is not None:
        stmt = stmt.where(Transaction.currency == currency.upper())

    txns = list(db.scalars(stmt).all())

    # Group by category
    buckets: dict[Optional[uuid.UUID], dict] = {}
    total_income = Decimal("0")
    total_expenses = Decimal("0")

    for txn in txns:
        cat = txn.category
        cat_id = cat.id if cat else None
        inc, exp = _categorise_amount(txn.amount)

        if cat_id not in buckets:
            buckets[cat_id] = {
                "category_id": cat_id,
                "category_name": cat.name if cat else "Uncategorized",
                "category_slug": cat.slug if cat else None,
                "category_icon": cat.icon if cat else None,
                "total_amount": Decimal("0"),
                "transaction_count": 0,
            }

        buckets[cat_id]["total_amount"] += abs(txn.amount)
        buckets[cat_id]["transaction_count"] += 1
        total_income += inc
        total_expenses += exp

    # Compute percentage per category
    total = total_income + total_expenses
    items = []
    for cat_id, data in buckets.items():
        pct = float(data["total_amount"] / total * 100) if total > 0 else 0.0
        items.append({
            "category_id": data["category_id"],
            "category_name": data["category_name"],
            "category_slug": data["category_slug"],
            "category_icon": data["category_icon"],
            "total_amount": data["total_amount"],
            "transaction_count": data["transaction_count"],
            "percentage": round(pct, 2),
        })

    items.sort(key=lambda x: x["total_amount"], reverse=True)

    return {
        "date_from": date_from,
        "date_to": date_to,
        "total_income": total_income,
        "total_expenses": total_expenses,
        "net": total_income - total_expenses,
        "categories": items,
    }


# ------------------------------------------------------------------
# Income vs expenses
# ------------------------------------------------------------------


def get_income_vs_expenses(
    db: Session,
    *,
    user_id: uuid.UUID,
    date_from: date,
    date_to: date,
    account_id: Optional[uuid.UUID] = None,
    currency: Optional[str] = None,
    monthly: bool = False,
) -> dict:
    stmt = (
        select(Transaction)
        .join(Account, Transaction.account_id == Account.id)
        .where(
            Account.user_id == user_id,
            Account.is_active,
            Transaction.status == TransactionStatus.BOOKED,
            Transaction.booking_date >= date_from,
            Transaction.booking_date <= date_to,
        )
    )
    if account_id is not None:
        stmt = stmt.where(Transaction.account_id == account_id)
    if currency is not None:
        stmt = stmt.where(Transaction.currency == currency.upper())

    txns = list(db.scalars(stmt).all())

    total_income = Decimal("0")
    total_expenses = Decimal("0")
    monthly_data: dict[tuple[int, int], dict] = {}

    for txn in txns:
        inc, exp = _categorise_amount(txn.amount)
        total_income += inc
        total_expenses += exp

        if monthly:
            key = (txn.booking_date.year, txn.booking_date.month)
            if key not in monthly_data:
                monthly_data[key] = {"income": Decimal("0"), "expenses": Decimal("0")}
            monthly_data[key]["income"] += inc
            monthly_data[key]["expenses"] += exp

    monthly_breakdown = []
    if monthly:
        for (year, month_num), data in sorted(monthly_data.items()):
            inc = data["income"]
            exp = data["expenses"]
            monthly_breakdown.append({
                "month": date(year, month_num, 1),
                "income": inc,
                "expenses": exp,
                "net": inc - exp,
            })

    return {
        "date_from": date_from,
        "date_to": date_to,
        "total_income": total_income,
        "total_expenses": total_expenses,
        "net": total_income - total_expenses,
        "monthly_breakdown": monthly_breakdown,
    }


# ------------------------------------------------------------------
# Monthly trends
# ------------------------------------------------------------------


def get_monthly_trends(
    db: Session,
    *,
    user_id: uuid.UUID,
    months: int = 12,
    account_id: Optional[uuid.UUID] = None,
    currency: Optional[str] = None,
) -> dict:
    today = date.today()
    start = date(today.year, today.month, 1) - timedelta(days=1)
    # Go back N months from the start of the current month
    for _ in range(months - 1):
        start = date(start.year, start.month, 1) - timedelta(days=1)
    date_from = date(start.year, start.month, 1)
    date_to = date(today.year, today.month, 1) - timedelta(days=1)

    stmt = (
        select(Transaction)
        .join(Account, Transaction.account_id == Account.id)
        .where(
            Account.user_id == user_id,
            Account.is_active,
            Transaction.status == TransactionStatus.BOOKED,
            Transaction.booking_date >= date_from,
            Transaction.booking_date <= date_to,
        )
    )
    if account_id is not None:
        stmt = stmt.where(Transaction.account_id == account_id)
    if currency is not None:
        stmt = stmt.where(Transaction.currency == currency.upper())

    txns = list(db.scalars(stmt).all())

    buckets: dict[tuple[int, int], dict] = {}
    for txn in txns:
        key = (txn.booking_date.year, txn.booking_date.month)
        if key not in buckets:
            buckets[key] = {"income": Decimal("0"), "expenses": Decimal("0")}
        inc, exp = _categorise_amount(txn.amount)
        buckets[key]["income"] += inc
        buckets[key]["expenses"] += exp

    data = []
    for (year, month_num), vals in sorted(buckets.items()):
        inc = vals["income"]
        exp = vals["expenses"]
        data.append({
            "month": date(year, month_num, 1),
            "income": inc,
            "expenses": exp,
            "net": inc - exp,
        })

    return {
        "months": months,
        "data": data,
    }


# ------------------------------------------------------------------
# Net worth
# ------------------------------------------------------------------


def get_net_worth(
    db: Session,
    *,
    user_id: uuid.UUID,
) -> dict:
    accounts = (
        db.scalars(
            select(Account).where(
                Account.user_id == user_id,
                Account.is_active,
            )
        )
        .all()
    )

    # Group accounts by type and classify as asset vs liability
    asset_types = {
        AccountType.CHECKING,
        AccountType.SAVINGS,
        AccountType.INVESTMENT,
    }
    liability_types = {
        AccountType.CREDIT_CARD,
        AccountType.LOAN,
    }

    total_assets = Decimal("0")
    total_liabilities = Decimal("0")
    by_type: dict[str, dict] = {}

    for acc in accounts:
        balance = acc.current_balance
        atype = acc.account_type

        if atype not in by_type:
            by_type[atype] = {"count": 0, "total_balance": Decimal("0")}
        by_type[atype]["count"] += 1
        by_type[atype]["total_balance"] += balance

        if atype in liability_types:
            total_liabilities += abs(balance) if balance < 0 else balance
        elif atype in asset_types:
            total_assets += balance if balance > 0 else Decimal("0")
        else:
            # OTHER — treat as asset if positive, ignore if negative
            if balance > 0:
                total_assets += balance

    # Add portfolio holdings market value
    holdings = (
        db.scalars(
            select(Holding).where(Holding.user_id == user_id)
        )
        .all()
    )
    portfolio_mv = Decimal("0")
    for h in holdings:
        if h.current_price is not None:
            portfolio_mv += h.quantity * h.current_price
    total_assets += portfolio_mv

    by_account_type = [
        {
            "account_type": atype,
            "count": data["count"],
            "total_balance": data["total_balance"],
        }
        for atype, data in sorted(by_type.items(), key=lambda x: x[0].value)
    ]

    return {
        "as_of_date": date.today(),
        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "net_worth": total_assets - total_liabilities,
        "by_account_type": by_account_type,
        "portfolio_market_value": portfolio_mv,
    }
