import uuid
from datetime import date
from decimal import Decimal

import jwt
import pytest
from sqlalchemy import select

from app.core.config import settings
from app.core.security import ALGORITHM
from app.models.account import Account, AccountType
from app.models.category import Category
from app.models.holding import AssetType, Holding
from app.models.transaction import Transaction, TransactionStatus
from app.models.user import User, UserRole
from app.services.report_service import (
    get_category_breakdown,
    get_income_vs_expenses,
    get_monthly_trends,
    get_net_worth,
)

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

@pytest.fixture()
def user(db_session):
    u = User(
        id=uuid.uuid4(),
        email="reports@example.com",
        hashed_password="x",
        full_name="Reports User",
        role=UserRole.USER,
    )
    db_session.add(u)
    db_session.commit()
    return u


def auth_header(user_id: uuid.UUID) -> dict:
    token = jwt.encode(
        {"sub": str(user_id), "type": "access"},
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def category_groceries(db_session):
    cat = Category(
        id=uuid.uuid4(), name="Groceries", slug="groceries",
        icon="shopping-cart", is_system=True,
    )
    db_session.add(cat)
    db_session.commit()
    return cat


@pytest.fixture()
def category_income(db_session):
    cat = Category(
        id=uuid.uuid4(), name="Income", slug="income",
        icon="trending-up", is_system=True,
    )
    db_session.add(cat)
    db_session.commit()
    return cat


@pytest.fixture()
def account_checking(db_session, user):
    acc = Account(
        id=uuid.uuid4(), user_id=user.id, bank_connection_id=uuid.uuid4(),
        external_account_id="ext-checking", display_name="Checking",
        account_type=AccountType.CHECKING, currency="USD",
        current_balance=Decimal("5000.00"),
    )
    db_session.add(acc)
    db_session.commit()
    return acc


@pytest.fixture()
def account_credit(db_session, user):
    acc = Account(
        id=uuid.uuid4(), user_id=user.id, bank_connection_id=uuid.uuid4(),
        external_account_id="ext-credit", display_name="Credit Card",
        account_type=AccountType.CREDIT_CARD, currency="USD",
        current_balance=Decimal("-1500.00"),
    )
    db_session.add(acc)
    db_session.commit()
    return acc


def create_txn(db_session, *, account, amount, booking_date,
               category=None, user_id=None):
    txn = Transaction(
        id=uuid.uuid4(),
        account_id=account.id,
        amount=amount,
        currency="USD",
        booking_date=booking_date,
        description="Test",
        status=TransactionStatus.BOOKED,
        category_id=category.id if category else None,
        dedupe_hash=f"hash-report-{uuid.uuid4().hex[:8]}",
    )
    db_session.add(txn)
    db_session.commit()
    return txn


# ------------------------------------------------------------------
# Category breakdown
# ------------------------------------------------------------------


class TestCategoryBreakdown:
    def test_empty_range(self, db_session, user, account_checking):
        result = get_category_breakdown(
            db_session, user_id=user.id,
            date_from=date(2026, 1, 1), date_to=date(2026, 1, 31),
        )
        assert result["total_income"] == Decimal("0")
        assert result["total_expenses"] == Decimal("0")
        assert result["categories"] == []

    def test_groups_by_category(self, db_session, user, account_checking,
                                category_groceries, category_income):
        create_txn(db_session, account=account_checking,
                   amount=Decimal("-120.00"), booking_date=date(2026, 7, 1),
                   category=category_groceries)
        create_txn(db_session, account=account_checking,
                   amount=Decimal("-45.99"), booking_date=date(2026, 7, 2),
                   category=category_groceries)
        create_txn(db_session, account=account_checking,
                   amount=Decimal("5000.00"), booking_date=date(2026, 7, 3),
                   category=category_income)

        result = get_category_breakdown(
            db_session, user_id=user.id,
            date_from=date(2026, 7, 1), date_to=date(2026, 7, 31),
        )
        assert result["total_income"] == Decimal("5000.00")
        assert result["total_expenses"] == Decimal("165.99")
        assert len(result["categories"]) == 2

        lookup = {c["category_slug"]: c for c in result["categories"]}
        assert lookup["groceries"]["transaction_count"] == 2
        assert lookup["groceries"]["total_amount"] == Decimal("165.99")
        assert lookup["income"]["transaction_count"] == 1
        assert lookup["income"]["total_amount"] == Decimal("5000.00")

    def test_uncategorized_transactions(self, db_session, user, account_checking):
        create_txn(db_session, account=account_checking,
                   amount=Decimal("-25.00"), booking_date=date(2026, 7, 5))
        result = get_category_breakdown(
            db_session, user_id=user.id,
            date_from=date(2026, 7, 1), date_to=date(2026, 7, 31),
        )
        assert len(result["categories"]) == 1
        assert result["categories"][0]["category_name"] == "Uncategorized"

    def test_pending_transactions_excluded(self, db_session, user, account_checking,
                                           category_groceries):
        txn = Transaction(
            id=uuid.uuid4(), account_id=account_checking.id,
            amount=Decimal("-50.00"), currency="USD",
            booking_date=date(2026, 7, 10), description="Pending",
            status=TransactionStatus.PENDING, category_id=category_groceries.id,
            dedupe_hash="hash-report-pending",
        )
        db_session.add(txn)
        db_session.commit()

        result = get_category_breakdown(
            db_session, user_id=user.id,
            date_from=date(2026, 7, 1), date_to=date(2026, 7, 31),
        )
        assert result["categories"] == []

    def test_filter_by_account(self, db_session, user, account_checking,
                               account_credit, category_groceries):
        create_txn(db_session, account=account_checking,
                   amount=Decimal("-100.00"), booking_date=date(2026, 7, 1),
                   category=category_groceries)
        create_txn(db_session, account=account_credit,
                   amount=Decimal("-50.00"), booking_date=date(2026, 7, 1),
                   category=category_groceries)

        result = get_category_breakdown(
            db_session, user_id=user.id,
            date_from=date(2026, 7, 1), date_to=date(2026, 7, 31),
            account_id=account_checking.id,
        )
        assert result["total_expenses"] == Decimal("100.00")

    def test_other_user_not_included(self, db_session, user, account_checking,
                                     category_groceries):
        other_user = User(
            id=uuid.uuid4(), email="other@example.com",
            hashed_password="x", full_name="Other", role=UserRole.USER,
        )
        db_session.add(other_user)
        db_session.commit()

        other_acc = Account(
            id=uuid.uuid4(), user_id=other_user.id, bank_connection_id=uuid.uuid4(),
            external_account_id="ext-other", display_name="Other",
            account_type=AccountType.CHECKING, currency="USD",
        )
        db_session.add(other_acc)
        db_session.commit()

        create_txn(db_session, account=other_acc,
                   amount=Decimal("-200.00"), booking_date=date(2026, 7, 1),
                   category=category_groceries)

        result = get_category_breakdown(
            db_session, user_id=user.id,
            date_from=date(2026, 7, 1), date_to=date(2026, 7, 31),
        )
        assert result["categories"] == []


# ------------------------------------------------------------------
# Income vs expenses
# ------------------------------------------------------------------


class TestIncomeVsExpenses:
    def test_totals_only(self, db_session, user, account_checking):
        create_txn(db_session, account=account_checking,
                   amount=Decimal("3000.00"), booking_date=date(2026, 6, 15))
        create_txn(db_session, account=account_checking,
                   amount=Decimal("-500.00"), booking_date=date(2026, 6, 20))
        create_txn(db_session, account=account_checking,
                   amount=Decimal("-200.00"), booking_date=date(2026, 7, 5))

        result = get_income_vs_expenses(
            db_session, user_id=user.id,
            date_from=date(2026, 6, 1), date_to=date(2026, 7, 31),
        )
        assert result["total_income"] == Decimal("3000.00")
        assert result["total_expenses"] == Decimal("700.00")
        assert result["net"] == Decimal("2300.00")
        assert len(result["monthly_breakdown"]) == 0

    def test_monthly_breakdown(self, db_session, user, account_checking):
        create_txn(db_session, account=account_checking,
                   amount=Decimal("2000.00"), booking_date=date(2026, 1, 15))
        create_txn(db_session, account=account_checking,
                   amount=Decimal("-800.00"), booking_date=date(2026, 1, 20))
        create_txn(db_session, account=account_checking,
                   amount=Decimal("2500.00"), booking_date=date(2026, 2, 10))
        create_txn(db_session, account=account_checking,
                   amount=Decimal("-900.00"), booking_date=date(2026, 2, 15))

        result = get_income_vs_expenses(
            db_session, user_id=user.id,
            date_from=date(2026, 1, 1), date_to=date(2026, 2, 28),
            monthly=True,
        )
        assert len(result["monthly_breakdown"]) == 2
        jan = result["monthly_breakdown"][0]
        assert jan["month"] == date(2026, 1, 1)
        assert jan["income"] == Decimal("2000.00")
        assert jan["expenses"] == Decimal("800.00")
        assert jan["net"] == Decimal("1200.00")
        feb = result["monthly_breakdown"][1]
        assert feb["month"] == date(2026, 2, 1)


# ------------------------------------------------------------------
# Monthly trends
# ------------------------------------------------------------------


class TestMonthlyTrends:
    def test_trend_data(self, db_session, user, account_checking):
        for m in range(1, 4):
            create_txn(db_session, account=account_checking,
                       amount=Decimal("3000.00"),
                       booking_date=date(2026, m, 15))
            create_txn(db_session, account=account_checking,
                       amount=Decimal("-1500.00"),
                       booking_date=date(2026, m, 20))

        result = get_monthly_trends(
            db_session, user_id=user.id, months=12,
        )
        assert len(result["data"]) == 3
        for point in result["data"]:
            assert point["income"] == Decimal("3000.00")
            assert point["expenses"] == Decimal("1500.00")
            assert point["net"] == Decimal("1500.00")

    def test_no_data(self, db_session, user):
        result = get_monthly_trends(
            db_session, user_id=user.id, months=6,
        )
        assert result["data"] == []

    def test_month_boundary_excludes_current_month(self, db_session, user, account_checking):
        create_txn(db_session, account=account_checking,
                   amount=Decimal("1000.00"), booking_date=date.today())
        result = get_monthly_trends(
            db_session, user_id=user.id, months=12,
        )
        # Today's month should be excluded from the trend window
        current_key = (date.today().year, date.today().month)
        for point in result["data"]:
            key = (point["month"].year, point["month"].month)
            assert key != current_key


# ------------------------------------------------------------------
# Net worth
# ------------------------------------------------------------------


class TestNetWorth:
    def test_assets_minus_liabilities(self, db_session, user,
                                      account_checking, account_credit):
        result = get_net_worth(db_session, user_id=user.id)
        assert result["total_assets"] == Decimal("5000.00")
        assert result["total_liabilities"] == Decimal("1500.00")
        assert result["net_worth"] == Decimal("3500.00")

    def test_includes_portfolio_value(self, db_session, user, account_checking):
        holding = Holding(
            id=uuid.uuid4(), user_id=user.id,
            symbol="AAPL", name="Apple",
            asset_type=AssetType.STOCK, currency="USD",
            quantity=Decimal("10"), current_price=Decimal("200.00"),
        )
        db_session.add(holding)
        db_session.commit()

        result = get_net_worth(db_session, user_id=user.id)
        assert result["portfolio_market_value"] == Decimal("2000.00")
        assert result["total_assets"] == Decimal("5000.00") + Decimal("2000.00")

    def test_by_account_type_breakdown(self, db_session, user,
                                       account_checking, account_credit):
        result = get_net_worth(db_session, user_id=user.id)
        lookup = {g["account_type"]: g for g in result["by_account_type"]}
        assert lookup["checking"]["count"] == 1
        assert lookup["checking"]["total_balance"] == Decimal("5000.00")
        assert lookup["credit_card"]["count"] == 1
        assert lookup["credit_card"]["total_balance"] == Decimal("-1500.00")

    def test_no_accounts(self, db_session, user):
        result = get_net_worth(db_session, user_id=user.id)
        assert result["total_assets"] == Decimal("0")
        assert result["total_liabilities"] == Decimal("0")
        assert result["net_worth"] == Decimal("0")


# ------------------------------------------------------------------
# Integration: API endpoints
# ------------------------------------------------------------------

API_PREFIX = "/api/v1/report"


class TestReportsAPI:
    def test_category_breakdown_endpoint(self, db_session, client, user,
                                         account_checking, category_groceries):
        create_txn(db_session, account=account_checking,
                   amount=Decimal("-50.00"), booking_date=date(2026, 7, 1),
                   category=category_groceries)
        resp = client.get(
            f"{API_PREFIX}/category-breakdown",
            params={"date_from": "2026-07-01", "date_to": "2026-07-31"},
            headers=auth_header(user.id),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_expenses"] == "50.0000"
        assert len(data["categories"]) == 1

    def test_income_vs_expenses_endpoint(self, db_session, client, user,
                                         account_checking):
        create_txn(db_session, account=account_checking,
                   amount=Decimal("1000.00"), booking_date=date(2026, 7, 1))
        create_txn(db_session, account=account_checking,
                   amount=Decimal("-300.00"), booking_date=date(2026, 7, 2))
        resp = client.get(
            f"{API_PREFIX}/income-vs-expenses",
            params={"date_from": "2026-07-01", "date_to": "2026-07-31"},
            headers=auth_header(user.id),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_income"] == "1000.0000"
        assert data["total_expenses"] == "300.0000"

    def test_income_vs_expenses_monthly(self, db_session, client, user,
                                        account_checking):
        create_txn(db_session, account=account_checking,
                   amount=Decimal("1000.00"), booking_date=date(2026, 7, 1))
        resp = client.get(
            f"{API_PREFIX}/income-vs-expenses",
            params={
                "date_from": "2026-07-01",
                "date_to": "2026-07-31",
                "monthly": "true",
            },
            headers=auth_header(user.id),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["monthly_breakdown"]) == 1

    def test_monthly_trends_endpoint(self, db_session, client, user,
                                     account_checking):
        create_txn(db_session, account=account_checking,
                   amount=Decimal("2000.00"), booking_date=date(2026, 7, 1))
        resp = client.get(
            f"{API_PREFIX}/monthly-trends",
            params={"months": "6"},
            headers=auth_header(user.id),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["months"] == 6

    def test_net_worth_endpoint(self, db_session, client, user,
                                account_checking):
        resp = client.get(
            f"{API_PREFIX}/net-worth",
            headers=auth_header(user.id),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["net_worth"] is not None

    def test_unauthorized(self, db_session, client):
        resp = client.get(
            f"{API_PREFIX}/net-worth",
        )
        assert resp.status_code == 401

    def test_category_breakdown_missing_dates(self, db_session, client, user):
        resp = client.get(
            f"{API_PREFIX}/category-breakdown",
            headers=auth_header(user.id),
        )
        assert resp.status_code == 422
