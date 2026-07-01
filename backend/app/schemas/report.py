import uuid
from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.account import AccountType


class ReportCategoryBreakdownItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    category_id: Optional[uuid.UUID] = None
    category_name: str = "Uncategorized"
    category_slug: Optional[str] = None
    category_icon: Optional[str] = None
    total_amount: Decimal = Decimal("0")
    transaction_count: int = 0
    percentage: float = 0.0


class ReportCategoryBreakdown(BaseModel):
    date_from: date
    date_to: date
    total_income: Decimal = Decimal("0")
    total_expenses: Decimal = Decimal("0")
    net: Decimal = Decimal("0")
    categories: list[ReportCategoryBreakdownItem] = []


class IncomeExpenseMonth(BaseModel):
    month: date
    income: Decimal = Decimal("0")
    expenses: Decimal = Decimal("0")
    net: Decimal = Decimal("0")


class ReportIncomeVsExpenses(BaseModel):
    date_from: date
    date_to: date
    total_income: Decimal = Decimal("0")
    total_expenses: Decimal = Decimal("0")
    net: Decimal = Decimal("0")
    monthly_breakdown: list[IncomeExpenseMonth] = []


class MonthlyTrendPoint(BaseModel):
    month: date
    income: Decimal = Decimal("0")
    expenses: Decimal = Decimal("0")
    net: Decimal = Decimal("0")


class ReportMonthlyTrends(BaseModel):
    months: int
    data: list[MonthlyTrendPoint] = []


class NetWorthAccountGroup(BaseModel):
    account_type: AccountType
    count: int = 0
    total_balance: Decimal = Decimal("0")


class ReportNetWorth(BaseModel):
    as_of_date: date
    total_assets: Decimal = Decimal("0")
    total_liabilities: Decimal = Decimal("0")
    net_worth: Decimal = Decimal("0")
    by_account_type: list[NetWorthAccountGroup] = []
    portfolio_market_value: Decimal = Decimal("0")
