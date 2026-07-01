import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.account import Account, AccountType
from app.models.bank_connection import BankConnection, BankProvider, ConnectionStatus
from app.models.category import Category
from app.models.transaction import (
    CategorySource,
    Transaction,
    TransactionStatus,
)
from app.models.user import User, UserRole
from app.services.transaction_service import (
    TransactionNotFoundError,
    create_manual_transaction,
    get_transaction,
    get_transactions,
    update_transaction_category,
)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

@pytest.fixture()
def user_with_data(db_session):
    u = User(
        id=uuid.uuid4(),
        email="txntest@example.com",
        hashed_password="x",
        full_name="Txn Test",
        role=UserRole.USER,
    )
    db_session.add(u)
    db_session.flush()

    conn = BankConnection(
        id=uuid.uuid4(), user_id=u.id,
        provider=BankProvider.NORDIGEN,
        institution_id="TEST", institution_name="Test Bank",
        external_reference="ref-txn",
        status=ConnectionStatus.LINKED,
    )
    db_session.add(conn)
    db_session.flush()

    acc = Account(
        id=uuid.uuid4(), user_id=u.id, bank_connection_id=conn.id,
        external_account_id="ext-txn", display_name="Txn Account",
        account_type=AccountType.CHECKING, currency="PLN",
    )
    db_session.add(acc)
    db_session.flush()

    cat = Category(
        id=uuid.uuid4(), name="Groceries", slug="groceries",
        icon="shopping-cart", is_system=True,
    )
    db_session.add(cat)
    db_session.flush()

    # Seed transactions
    txns = [
        Transaction(
            id=uuid.uuid4(), account_id=acc.id,
            amount=Decimal("-120.00"), currency="PLN",
            booking_date=date(2026, 7, 5), description="Lidl",
            status=TransactionStatus.BOOKED, category_id=cat.id,
            category_source=CategorySource.RULE,
            dedupe_hash="hash-txn-1",
        ),
        Transaction(
            id=uuid.uuid4(), account_id=acc.id,
            amount=Decimal("-45.99"), currency="PLN",
            booking_date=date(2026, 7, 10), description="Biedronka",
            status=TransactionStatus.BOOKED, category_id=cat.id,
            category_source=CategorySource.ML,
            dedupe_hash="hash-txn-2",
        ),
        Transaction(
            id=uuid.uuid4(), account_id=acc.id,
            amount=Decimal("5000.00"), currency="PLN",
            booking_date=date(2026, 7, 1), description="Salary",
            status=TransactionStatus.BOOKED,
            dedupe_hash="hash-txn-3",
        ),
        Transaction(
            id=uuid.uuid4(), account_id=acc.id,
            amount=Decimal("-200.00"), currency="PLN",
            booking_date=date(2026, 8, 1), description="August rent",
            status=TransactionStatus.PENDING,
            dedupe_hash="hash-txn-4",
        ),
    ]
    db_session.add_all(txns)
    db_session.commit()
    return u, acc, cat, txns


def token_header(client, user):
    from app.core.security import create_access_token
    token = create_access_token(user.id, user.role.value)
    return {"Authorization": f"Bearer {token}"}


# ------------------------------------------------------------------
# Unit: service layer
# ------------------------------------------------------------------


class TestGetTransactions:
    def test_lists_all(self, db_session, user_with_data):
        user, acc, cat, txns = user_with_data
        result, total = get_transactions(db_session, user_id=user.id)
        assert total == 4
        assert len(result) == 4

    def test_filters_by_account(self, db_session, user_with_data):
        user, acc, cat, txns = user_with_data
        result, total = get_transactions(db_session, user_id=user.id, account_id=acc.id)
        assert total == 4

    def test_filters_by_category(self, db_session, user_with_data):
        user, acc, cat, txns = user_with_data
        result, total = get_transactions(db_session, user_id=user.id, category_id=cat.id)
        assert total == 2

    def test_filters_by_date_range(self, db_session, user_with_data):
        user, acc, cat, txns = user_with_data
        result, total = get_transactions(
            db_session, user_id=user.id,
            date_from=date(2026, 7, 1), date_to=date(2026, 7, 31),
        )
        assert total == 3

    def test_filters_by_status(self, db_session, user_with_data):
        user, acc, cat, txns = user_with_data
        result, total = get_transactions(
            db_session, user_id=user.id,
            status=TransactionStatus.PENDING,
        )
        assert total == 1

    def test_search_description(self, db_session, user_with_data):
        user, acc, cat, txns = user_with_data
        result, total = get_transactions(db_session, user_id=user.id, search="lidl")
        assert total == 1

    def test_pagination(self, db_session, user_with_data):
        user, acc, cat, txns = user_with_data
        result, total = get_transactions(db_session, user_id=user.id, offset=0, limit=2)
        assert len(result) == 2
        assert total == 4

    def test_other_user_excluded(self, db_session, user_with_data):
        user, acc, cat, txns = user_with_data
        other = User(
            id=uuid.uuid4(), email="other@example.com",
            hashed_password="x", full_name="Other", role=UserRole.USER,
        )
        db_session.add(other)
        db_session.commit()
        result, total = get_transactions(db_session, user_id=other.id)
        assert total == 0


class TestGetTransaction:
    def test_found(self, db_session, user_with_data):
        user, acc, cat, txns = user_with_data
        txn = get_transaction(db_session, transaction_id=txns[0].id, user_id=user.id)
        assert txn.id == txns[0].id

    def test_not_found_raises(self, db_session, user_with_data):
        user, acc, cat, txns = user_with_data
        with pytest.raises(TransactionNotFoundError):
            get_transaction(db_session, transaction_id=uuid.uuid4(), user_id=user.id)


class TestUpdateTransactionCategory:
    def test_updates_category(self, db_session, user_with_data):
        user, acc, cat, txns = user_with_data
        uncategorized = txns[2]  # Salary — no category
        updated = update_transaction_category(
            db_session,
            transaction_id=uncategorized.id,
            user_id=user.id,
            category_id=cat.id,
            category_source=CategorySource.USER,
        )
        assert updated.category_id == cat.id
        assert updated.category_source == CategorySource.USER
        assert updated.category_confidence == 1.0

    def test_not_found_raises(self, db_session, user_with_data):
        user, acc, cat, txns = user_with_data
        with pytest.raises(TransactionNotFoundError):
            update_transaction_category(
                db_session,
                transaction_id=uuid.uuid4(),
                user_id=user.id,
                category_id=cat.id,
            )


class TestCreateManualTransaction:
    def test_creates(self, db_session, user_with_data):
        user, acc, cat, txns = user_with_data
        txn = create_manual_transaction(
            db_session,
            account_id=acc.id,
            user_id=user.id,
            amount=Decimal("-89.99"),
            currency="PLN",
            booking_date=date(2026, 8, 15),
            description="Manual entry",
            counterparty_name="Some Store",
            category_id=cat.id,
        )
        assert txn.amount == Decimal("-89.99")
        assert txn.description == "Manual entry"
        assert txn.counterparty_name == "Some Store"
        assert txn.category_id == cat.id
        assert txn.status == TransactionStatus.BOOKED
        assert txn.external_id is None

    def test_raises_on_missing_account(self, db_session, user_with_data):
        user, acc, cat, txns = user_with_data
        from app.services.account_service import AccountNotFoundError
        with pytest.raises(AccountNotFoundError):
            create_manual_transaction(
                db_session,
                account_id=uuid.uuid4(),
                user_id=user.id,
                amount=Decimal("-10.00"),
                currency="PLN",
                booking_date=date(2026, 8, 1),
                description="Bad account",
            )


# ------------------------------------------------------------------
# Integration: API endpoints
# ------------------------------------------------------------------

API_PREFIX = "/api/v1/transactions"


class TestTransactionAPI:
    def test_list(self, db_session, client, user_with_data):
        user, acc, cat, txns = user_with_data
        resp = client.get(API_PREFIX, headers=token_header(client, user))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 4

    def test_list_with_filters(self, db_session, client, user_with_data):
        user, acc, cat, txns = user_with_data
        resp = client.get(
            f"{API_PREFIX}?status=pending",
            headers=token_header(client, user),
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_get_single(self, db_session, client, user_with_data):
        user, acc, cat, txns = user_with_data
        resp = client.get(
            f"{API_PREFIX}/{txns[0].id}",
            headers=token_header(client, user),
        )
        assert resp.status_code == 200
        assert resp.json()["description"] == "Lidl"

    def test_get_not_found(self, db_session, client, user_with_data):
        user, acc, cat, txns = user_with_data
        resp = client.get(
            f"{API_PREFIX}/{uuid.uuid4()}",
            headers=token_header(client, user),
        )
        assert resp.status_code == 404

    def test_update_category(self, db_session, client, user_with_data):
        user, acc, cat, txns = user_with_data
        target = txns[2]  # uncategorized Salary
        resp = client.patch(
            f"{API_PREFIX}/{target.id}",
            json={"category_id": str(cat.id), "category_source": "user"},
            headers=token_header(client, user),
        )
        assert resp.status_code == 200
        assert resp.json()["category_id"] == str(cat.id)

    def test_update_not_found(self, db_session, client, user_with_data):
        user, acc, cat, txns = user_with_data
        resp = client.patch(
            f"{API_PREFIX}/{uuid.uuid4()}",
            json={"category_id": str(cat.id), "category_source": "user"},
            headers=token_header(client, user),
        )
        assert resp.status_code == 404

    def test_create_manual(self, db_session, client, user_with_data):
        user, acc, cat, txns = user_with_data
        resp = client.post(
            API_PREFIX,
            json={
                "account_id": str(acc.id),
                "amount": "-49.99",
                "currency": "PLN",
                "booking_date": "2026-08-20",
                "description": "Manual via API",
            },
            headers=token_header(client, user),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["description"] == "Manual via API"
        assert Decimal(data["amount"]) == Decimal("-49.99")

    def test_create_manual_account_not_found(self, db_session, client, user_with_data):
        user, acc, cat, txns = user_with_data
        resp = client.post(
            API_PREFIX,
            json={
                "account_id": str(uuid.uuid4()),
                "amount": "-10.00",
                "currency": "PLN",
                "booking_date": "2026-08-20",
                "description": "Bad account",
            },
            headers=token_header(client, user),
        )
        assert resp.status_code == 404

    def test_unauthorized(self, client):
        resp = client.get(API_PREFIX)
        assert resp.status_code == 401
