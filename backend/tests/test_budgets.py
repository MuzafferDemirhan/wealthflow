import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.budget import Budget
from app.models.category import Category
from app.models.transaction import Transaction, TransactionStatus
from app.models.user import User, UserRole
from app.services.budget_service import (
    BudgetConflictError,
    BudgetNotFoundError,
    create_budget,
    delete_budget,
    get_user_budgets,
    update_budget,
)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

@pytest.fixture()
def user(db_session):
    u = User(
        id=uuid.uuid4(),
        email="budgets@example.com",
        hashed_password="x",
        full_name="Budget User",
        role=UserRole.USER,
    )
    db_session.add(u)
    db_session.commit()
    return u


@pytest.fixture()
def category(db_session):
    cat = Category(
        id=uuid.uuid4(), name="Groceries", slug="groceries",
        icon="shopping-cart", is_system=True,
    )
    db_session.add(cat)
    db_session.commit()
    return cat


def auth_header(client, user):
    """Register + login to get a real token."""
    token = _login_and_get_token(client, user)
    return {"Authorization": f"Bearer {token}"}


def _login_and_get_token(client, user):
    from app.core.security import create_access_token
    return create_access_token(user.id, user.role.value)


# ------------------------------------------------------------------
# Unit: service layer helpers
# ------------------------------------------------------------------


class TestGetNextMonthStart:
    def test_december_rolls_over(self):
        from app.services.budget_service import _get_next_month_start
        result = _get_next_month_start(2026, 12)
        assert result == date(2027, 1, 1)

    def test_mid_year(self):
        from app.services.budget_service import _get_next_month_start
        result = _get_next_month_start(2026, 6)
        assert result == date(2026, 7, 1)


class TestComputeSpending:
    def test_returns_sum_for_category(self, db_session, user, category):
        from app.services.budget_service import _compute_spending
        from app.models.account import Account, AccountType

        acc = Account(
            id=uuid.uuid4(), user_id=user.id, bank_connection_id=uuid.uuid4(),
            external_account_id="ext", display_name="Test",
            account_type=AccountType.CHECKING, currency="PLN",
        )
        db_session.add(acc)
        db_session.commit()

        txn1 = Transaction(id=uuid.uuid4(), account_id=acc.id,
                    amount=Decimal("-120.00"), currency="PLN",
                    booking_date=date(2026, 7, 5), description="Lidl",
                    status=TransactionStatus.BOOKED, category_id=category.id,
                    dedupe_hash="hash-budget-1")
        txn2 = Transaction(id=uuid.uuid4(), account_id=acc.id,
                    amount=Decimal("-45.99"), currency="PLN",
                    booking_date=date(2026, 7, 15), description="Biedronka",
                    status=TransactionStatus.BOOKED, category_id=category.id,
                    dedupe_hash="hash-budget-2")
        db_session.add_all([txn1, txn2])
        db_session.commit()

        spent = _compute_spending(
            db_session, user_id=user.id,
            category_id=category.id,
            period_month=date(2026, 7, 1),
        )
        assert spent == Decimal("-165.99")

    def test_excludes_next_month(self, db_session, user, category):
        from app.services.budget_service import _compute_spending
        from app.models.account import Account, AccountType

        acc = Account(
            id=uuid.uuid4(), user_id=user.id, bank_connection_id=uuid.uuid4(),
            external_account_id="ext2", display_name="Test2",
            account_type=AccountType.CHECKING, currency="PLN",
        )
        db_session.add(acc)
        db_session.commit()

        txn = Transaction(id=uuid.uuid4(), account_id=acc.id,
                    amount=Decimal("-50.00"), currency="PLN",
                    booking_date=date(2026, 8, 1), description="Aug",
                    status=TransactionStatus.BOOKED, category_id=category.id,
                    dedupe_hash="hash-budget-3")
        db_session.add(txn)
        db_session.commit()

        spent = _compute_spending(
            db_session, user_id=user.id,
            category_id=category.id,
            period_month=date(2026, 7, 1),
        )
        assert spent == Decimal("0")


# ------------------------------------------------------------------
# Unit: service layer CRUD
# ------------------------------------------------------------------


class TestCreateBudget:
    def test_creates_budget(self, db_session, user, category):
        budget = create_budget(
            db_session,
            user_id=user.id,
            category_id=category.id,
            period_month=date(2026, 8, 1),
            amount_limit=Decimal("2000.00"),
            currency="PLN",
        )
        assert budget.amount_limit == Decimal("2000.00")
        assert budget.category_id == category.id

    def test_raises_on_duplicate(self, db_session, user, category):
        create_budget(
            db_session, user_id=user.id, category_id=category.id,
            period_month=date(2026, 8, 1), amount_limit=Decimal("1000"), currency="PLN",
        )
        with pytest.raises(BudgetConflictError):
            create_budget(
                db_session, user_id=user.id, category_id=category.id,
                period_month=date(2026, 8, 1), amount_limit=Decimal("2000"), currency="PLN",
            )


class TestGetUserBudgets:
    def test_returns_budgets_with_spending(self, db_session, user, category):
        from app.models.account import Account, AccountType

        acc = Account(
            id=uuid.uuid4(), user_id=user.id, bank_connection_id=uuid.uuid4(),
            external_account_id="ext3", display_name="Test3",
            account_type=AccountType.CHECKING, currency="PLN",
        )
        db_session.add(acc)
        db_session.commit()

        create_budget(
            db_session, user_id=user.id, category_id=category.id,
            period_month=date(2026, 7, 1), amount_limit=Decimal("1000"), currency="PLN",
        )

        txn = Transaction(id=uuid.uuid4(), account_id=acc.id,
                    amount=Decimal("-300.00"), currency="PLN",
                    booking_date=date(2026, 7, 15), description="Spend",
                    status=TransactionStatus.BOOKED, category_id=category.id,
                    dedupe_hash="hash-budget-4")
        db_session.add(txn)
        db_session.commit()

        budgets = get_user_budgets(db_session, user_id=user.id)
        assert len(budgets) == 1
        b = budgets[0]
        assert b["spent"] == Decimal("300.00")
        assert b["remaining"] == Decimal("700.00")
        assert b["progress_pct"] == 30.0

    def test_other_user_excluded(self, db_session, user, category):
        other = User(
            id=uuid.uuid4(), email="other@example.com",
            hashed_password="x", full_name="Other", role=UserRole.USER,
        )
        db_session.add(other)
        db_session.commit()
        create_budget(
            db_session, user_id=other.id, category_id=category.id,
            period_month=date(2026, 7, 1), amount_limit=Decimal("500"), currency="PLN",
        )
        budgets = get_user_budgets(db_session, user_id=user.id)
        assert len(budgets) == 0


class TestUpdateBudget:
    def test_updates_limit_and_category(self, db_session, user, category):
        budget = create_budget(
            db_session, user_id=user.id, category_id=None,
            period_month=date(2026, 7, 1), amount_limit=Decimal("500"), currency="PLN",
        )
        updated = update_budget(
            db_session, budget_id=budget.id, user_id=user.id,
            amount_limit=Decimal("1000"), category_id=category.id,
        )
        assert updated.amount_limit == Decimal("1000")
        assert updated.category_id == category.id

    def test_not_found_raises(self, db_session, user):
        with pytest.raises(BudgetNotFoundError):
            update_budget(
                db_session, budget_id=uuid.uuid4(), user_id=user.id,
            )


class TestDeleteBudget:
    def test_deletes(self, db_session, user):
        budget = create_budget(
            db_session, user_id=user.id, category_id=None,
            period_month=date(2026, 7, 1), amount_limit=Decimal("500"), currency="PLN",
        )
        delete_budget(db_session, budget_id=budget.id, user_id=user.id)
        stmt = select(Budget).where(Budget.id == budget.id)
        assert db_session.scalar(stmt) is None

    def test_not_found_raises(self, db_session, user):
        with pytest.raises(BudgetNotFoundError):
            delete_budget(db_session, budget_id=uuid.uuid4(), user_id=user.id)


# ------------------------------------------------------------------
# Integration: API endpoints
# ------------------------------------------------------------------

API_PREFIX = "/api/v1/budgets"


class TestBudgetAPI:
    def test_list_empty(self, db_session, client, user):
        token = _login_and_get_token(client, user)
        resp = client.get(API_PREFIX, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json() == []

    def test_create_and_list(self, db_session, client, user, category):
        token = _login_and_get_token(client, user)
        resp = client.post(
            API_PREFIX,
            json={
                "category_id": str(category.id),
                "period_month": "2026-08-01",
                "amount_limit": "1500.00",
                "currency": "PLN",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert Decimal(data["amount_limit"]) == Decimal("1500.00")
        assert data["category_id"] == str(category.id)

        resp2 = client.get(API_PREFIX, headers={"Authorization": f"Bearer {token}"})
        assert len(resp2.json()) == 1

    def test_create_duplicate_returns_409(self, db_session, client, user, category):
        token = _login_and_get_token(client, user)
        payload = {
            "category_id": str(category.id),
            "period_month": "2026-08-01",
            "amount_limit": "1000.00",
            "currency": "PLN",
        }
        client.post(API_PREFIX, json=payload, headers={"Authorization": f"Bearer {token}"})
        resp = client.post(API_PREFIX, json=payload, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 409

    def test_update(self, db_session, client, user, category):
        token = _login_and_get_token(client, user)
        resp = client.post(
            API_PREFIX,
            json={
                "category_id": str(category.id),
                "period_month": "2026-09-01",
                "amount_limit": "1000.00",
                "currency": "PLN",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        budget_id = resp.json()["id"]

        resp2 = client.put(
            f"{API_PREFIX}/{budget_id}",
            json={"amount_limit": "2000.00", "category_id": None},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp2.status_code == 200
        assert Decimal(resp2.json()["amount_limit"]) == Decimal("2000.00")

    def test_update_not_found(self, db_session, client, user):
        token = _login_and_get_token(client, user)
        resp = client.put(
            f"{API_PREFIX}/{uuid.uuid4()}",
            json={"amount_limit": "500.00"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    def test_delete(self, db_session, client, user, category):
        token = _login_and_get_token(client, user)
        resp = client.post(
            API_PREFIX,
            json={
                "category_id": str(category.id),
                "period_month": "2026-10-01",
                "amount_limit": "500.00",
                "currency": "PLN",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        budget_id = resp.json()["id"]

        resp2 = client.delete(
            f"{API_PREFIX}/{budget_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp2.status_code == 204

        resp3 = client.get(API_PREFIX, headers={"Authorization": f"Bearer {token}"})
        assert len(resp3.json()) == 0

    def test_unauthorized(self, client):
        resp = client.get(API_PREFIX)
        assert resp.status_code == 401

    def test_delete_not_found(self, db_session, client, user):
        token = _login_and_get_token(client, user)
        resp = client.delete(
            f"{API_PREFIX}/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404
