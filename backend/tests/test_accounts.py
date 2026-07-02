import uuid
from decimal import Decimal
from unittest.mock import patch

import pytest
from sqlalchemy import select

from app.models.account import Account, AccountType
from app.models.bank_connection import BankConnection, BankProvider, ConnectionStatus
from app.models.user import User, UserRole

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

@pytest.fixture()
def user_with_accounts(db_session):
    u = User(
        id=uuid.uuid4(),
        email="acctest@example.com",
        hashed_password="x",
        full_name="Account Test",
        role=UserRole.USER,
    )
    db_session.add(u)
    db_session.flush()

    conn = BankConnection(
        id=uuid.uuid4(), user_id=u.id,
        provider=BankProvider.NORDIGEN,
        institution_id="TEST", institution_name="Test Bank",
        external_reference="ref-acctest",
        status=ConnectionStatus.LINKED,
    )
    db_session.add(conn)
    db_session.flush()

    acc1 = Account(
        id=uuid.uuid4(), user_id=u.id, bank_connection_id=conn.id,
        external_account_id="ext-1", display_name="Checking",
        account_type=AccountType.CHECKING, currency="USD",
        current_balance=Decimal("1500.00"),
    )
    acc2 = Account(
        id=uuid.uuid4(), user_id=u.id, bank_connection_id=conn.id,
        external_account_id="ext-2", display_name="Savings",
        account_type=AccountType.SAVINGS, currency="USD",
        current_balance=Decimal("5000.00"),
    )
    db_session.add_all([acc1, acc2])
    db_session.commit()
    return u, conn, [acc1, acc2]


def token_header(client, user):
    from app.core.security import create_access_token
    token = create_access_token(user.id, user.role.value)
    return {"Authorization": f"Bearer {token}"}


# ------------------------------------------------------------------
# Integration: Account API endpoints
# ------------------------------------------------------------------

API_PREFIX = "/api/v1/account"


class TestAccountAPI:
    def test_list_accounts(self, db_session, client, user_with_accounts):
        user, conn, accounts = user_with_accounts
        resp = client.get(API_PREFIX, headers=token_header(client, user))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["display_name"] in ("Checking", "Savings")

    def test_list_empty_for_other_user(self, db_session, client, user_with_accounts):
        user, conn, accounts = user_with_accounts
        other = User(
            id=uuid.uuid4(), email="other@example.com",
            hashed_password="x", full_name="Other", role=UserRole.USER,
        )
        db_session.add(other)
        db_session.commit()
        resp = client.get(API_PREFIX, headers=token_header(client, other))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_account(self, db_session, client, user_with_accounts):
        user, conn, accounts = user_with_accounts
        resp = client.get(
            f"{API_PREFIX}/{accounts[0].id}",
            headers=token_header(client, user),
        )
        assert resp.status_code == 200
        assert resp.json()["display_name"] == "Checking"

    def test_get_account_not_found(self, db_session, client, user_with_accounts):
        user, conn, accounts = user_with_accounts
        resp = client.get(
            f"{API_PREFIX}/{uuid.uuid4()}",
            headers=token_header(client, user),
        )
        assert resp.status_code == 404

    def test_get_account_wrong_user(self, db_session, client, user_with_accounts):
        user, conn, accounts = user_with_accounts
        other = User(
            id=uuid.uuid4(), email="other2@example.com",
            hashed_password="x", full_name="Other2", role=UserRole.USER,
        )
        db_session.add(other)
        db_session.commit()
        resp = client.get(
            f"{API_PREFIX}/{accounts[0].id}",
            headers=token_header(client, other),
        )
        assert resp.status_code == 404

    def test_deactivate_account(self, db_session, client, user_with_accounts):
        user, conn, accounts = user_with_accounts
        resp = client.delete(
            f"{API_PREFIX}/{accounts[0].id}",
            headers=token_header(client, user),
        )
        assert resp.status_code == 204

        db_session.refresh(accounts[0])
        assert accounts[0].is_active is False

    def test_deactivate_not_found(self, db_session, client, user_with_accounts):
        user, conn, accounts = user_with_accounts
        resp = client.delete(
            f"{API_PREFIX}/{uuid.uuid4()}",
            headers=token_header(client, user),
        )
        assert resp.status_code == 404

    def test_sync_account(self, db_session, client, user_with_accounts):
        user, conn, accounts = user_with_accounts
        with patch("app.core.celery_app.celery_app.send_task") as mock_send:
            resp = client.post(
                f"{API_PREFIX}/{accounts[0].id}/sync",
                headers=token_header(client, user),
            )
        assert resp.status_code == 202
        mock_send.assert_called_once_with(
            "ingestion.sync_account_transactions",
            args=[str(accounts[0].id)],
        )

    def test_sync_not_found(self, db_session, client, user_with_accounts):
        user, conn, accounts = user_with_accounts
        resp = client.post(
            f"{API_PREFIX}/{uuid.uuid4()}/sync",
            headers=token_header(client, user),
        )
        assert resp.status_code == 404

    def test_unauthorized(self, client):
        resp = client.get(API_PREFIX)
        assert resp.status_code == 401

