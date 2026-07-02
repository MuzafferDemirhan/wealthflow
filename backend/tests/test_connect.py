import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import jwt
import pytest
from sqlalchemy import select

from app.core.config import settings
from app.core.security import ALGORITHM
from app.models.account import Account, AccountType
from app.models.bank_connection import BankConnection, BankProvider, ConnectionStatus
from app.models.user import User, UserRole
from app.services import connect_service
from app.services.connect_service import (
    ConnectError,
    ConnectionNotFoundError,
    InstitutionNotFoundError,
    RequisitionNotFoundError,
    _normalise_status,
)
from app.services.providers.base import ProviderAccount
from app.services.providers.nordigen import ProviderError

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

@pytest.fixture()
def user(db_session):
    u = User(
        id=uuid.uuid4(),
        email="connect@example.com",
        hashed_password="x",
        full_name="Connect User",
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


MOCK_INSTITUTIONS = [
    {"id": "SANDBOX_BANK", "name": "Sandbox Bank", "logo": None},
    {"id": "TEST_BANK", "name": "Test Bank", "logo": "https://example.com/logo.png"},
]


# ------------------------------------------------------------------
# Unit: _normalise_status
# ------------------------------------------------------------------


class TestNormaliseStatus:
    def test_linked(self):
        assert _normalise_status("LN") == ConnectionStatus.LINKED

    def test_pending(self):
        for s in ["CR", "GC", "UA", "GA"]:
            assert _normalise_status(s) == ConnectionStatus.PENDING

    def test_error(self):
        assert _normalise_status("RJ") == ConnectionStatus.ERROR

    def test_expired(self):
        assert _normalise_status("EX") == ConnectionStatus.EXPIRED

    def test_revoked(self):
        assert _normalise_status("SA") == ConnectionStatus.REVOKED

    def test_unknown(self):
        assert _normalise_status("XX") == ConnectionStatus.ERROR


# ------------------------------------------------------------------
# Unit: service layer (mocked provider)
# ------------------------------------------------------------------


class TestListInstitutions:
    @patch("app.services.connect_service._build_provider")
    def test_returns_sorted_list(self, mock_build):
        mock_provider = MagicMock()
        mock_provider.list_institutions.return_value = MOCK_INSTITUTIONS
        mock_build.return_value = mock_provider

        result = connect_service.list_institutions(country="PL")
        assert len(result) == 2
        assert result[0]["name"] == "Sandbox Bank"  # alphabetical

    @patch("app.services.connect_service._build_provider")
    def test_provider_error_raises_connect_error(self, mock_build):
        mock_provider = MagicMock()
        mock_provider.list_institutions.side_effect = ProviderError("API down")
        mock_build.return_value = mock_provider

        with pytest.raises(ConnectError):
            connect_service.list_institutions()


class TestCreateRequisition:
    @patch("app.services.connect_service._build_provider")
    def test_creates_connection(self, mock_build, db_session, user):
        mock_provider = MagicMock()
        mock_provider.list_institutions.return_value = MOCK_INSTITUTIONS
        mock_provider.create_requisition.return_value = {
            "id": "req-123",
            "link": "https://bank.link/start",
        }
        mock_build.return_value = mock_provider

        result = connect_service.create_requisition(
            db_session,
            user_id=user.id,
            institution_id="SANDBOX_BANK",
            redirect_uri="https://example.com/callback",
        )
        assert result["requisition_id"] == "req-123"
        assert result["link"] == "https://bank.link/start"
        assert result["status"] == ConnectionStatus.PENDING

        # Verify DB
        conn = db_session.scalar(select(BankConnection))
        assert conn is not None
        assert conn.user_id == user.id
        assert conn.external_reference == "req-123"
        assert conn.status == ConnectionStatus.PENDING

    @patch("app.services.connect_service._build_provider")
    def test_institution_not_found(self, mock_build, db_session, user):
        mock_provider = MagicMock()
        mock_provider.list_institutions.return_value = MOCK_INSTITUTIONS
        mock_build.return_value = mock_provider

        with pytest.raises(InstitutionNotFoundError):
            connect_service.create_requisition(
                db_session,
                user_id=user.id,
                institution_id="NONEXISTENT",
                redirect_uri="https://example.com/callback",
            )


class TestPollRequisition:
    @patch("app.services.connect_service._build_provider")
    def test_polls_and_links(self, mock_build, db_session, user):
        # Arrange: create a PENDING connection
        conn = BankConnection(
            id=uuid.uuid4(),
            user_id=user.id,
            provider=BankProvider.NORDIGEN,
            institution_id="SANDBOX_BANK",
            institution_name="Sandbox Bank",
            external_reference="req-456",
            status=ConnectionStatus.PENDING,
        )
        db_session.add(conn)
        db_session.commit()

        mock_provider = MagicMock()
        mock_provider.get_requisition.return_value = {"status": "LN"}
        mock_provider.fetch_accounts.return_value = [
            ProviderAccount(
                external_account_id="ext-acc-1",
                iban="PL123",
                currency="PLN",
                display_name="My Account",
                account_type="checking",
                current_balance=Decimal("1000.00"),
                balance_as_of=datetime.now(timezone.utc),
            ),
        ]
        mock_build.return_value = mock_provider

        result = connect_service.poll_requisition(
            db_session, connection_id=conn.id, user_id=user.id,
        )
        assert result["status"] == ConnectionStatus.LINKED
        assert len(result["accounts_created"]) == 1

        # Verify DB
        db_session.refresh(conn)
        assert conn.status == ConnectionStatus.LINKED

        account = db_session.scalar(select(Account))
        assert account is not None
        assert account.external_account_id == "ext-acc-1"
        assert account.user_id == user.id

    @patch("app.services.connect_service._build_provider")
    def test_already_linked_returns_cached(self, mock_build, db_session, user):
        conn = BankConnection(
            id=uuid.uuid4(),
            user_id=user.id,
            provider=BankProvider.NORDIGEN,
            institution_id="SANDBOX_BANK",
            institution_name="Sandbox Bank",
            external_reference="req-789",
            status=ConnectionStatus.LINKED,
        )
        db_session.add(conn)
        db_session.commit()

        result = connect_service.poll_requisition(
            db_session, connection_id=conn.id, user_id=user.id,
        )
        assert result["status"] == ConnectionStatus.LINKED
        mock_build.assert_not_called()

    def test_not_found(self, db_session, user):
        with pytest.raises(RequisitionNotFoundError):
            connect_service.poll_requisition(
                db_session, connection_id=uuid.uuid4(), user_id=user.id,
            )


class TestGetUserConnections:
    def test_returns_user_connections(self, db_session, user):
        conn = BankConnection(
            id=uuid.uuid4(),
            user_id=user.id,
            provider=BankProvider.NORDIGEN,
            institution_id="TEST",
            institution_name="Test Bank",
            external_reference="ref-1",
            status=ConnectionStatus.LINKED,
        )
        db_session.add(conn)
        db_session.commit()

        result = connect_service.get_user_connections(db_session, user_id=user.id)
        assert len(result) == 1
        assert result[0].external_reference == "ref-1"

    def test_other_user_not_included(self, db_session, user):
        other_user = User(
            id=uuid.uuid4(), email="other@example.com",
            hashed_password="x", full_name="Other", role=UserRole.USER,
        )
        db_session.add(other_user)
        db_session.commit()

        conn = BankConnection(
            id=uuid.uuid4(),
            user_id=other_user.id,
            provider=BankProvider.NORDIGEN,
            institution_id="TEST",
            institution_name="Test Bank",
            external_reference="ref-other",
            status=ConnectionStatus.LINKED,
        )
        db_session.add(conn)
        db_session.commit()

        result = connect_service.get_user_connections(db_session, user_id=user.id)
        assert len(result) == 0


class TestDisconnectConnection:
    def test_revokes_and_deactivates_accounts(self, db_session, user):
        conn = BankConnection(
            id=uuid.uuid4(),
            user_id=user.id,
            provider=BankProvider.NORDIGEN,
            institution_id="TEST",
            institution_name="Test Bank",
            external_reference="ref-disconnect",
            status=ConnectionStatus.LINKED,
        )
        db_session.add(conn)
        db_session.flush()

        acc = Account(
            id=uuid.uuid4(),
            user_id=user.id,
            bank_connection_id=conn.id,
            external_account_id="ext-disconnect",
            display_name="Disconnect Me",
            account_type=AccountType.CHECKING,
            currency="PLN",
        )
        db_session.add(acc)
        db_session.commit()

        connect_service.disconnect_connection(
            db_session, connection_id=conn.id, user_id=user.id,
        )

        db_session.refresh(conn)
        assert conn.status == ConnectionStatus.REVOKED

        db_session.refresh(acc)
        assert acc.is_active is False

    def test_not_found(self, db_session, user):
        with pytest.raises(ConnectionNotFoundError):
            connect_service.disconnect_connection(
                db_session, connection_id=uuid.uuid4(), user_id=user.id,
            )


# ------------------------------------------------------------------
# Integration: API endpoints
# ------------------------------------------------------------------

API_PREFIX = "/api/v1/connect"


class TestConnectAPI:
    def test_institutions_unauthenticated(self, client):
        resp = client.get(f"{API_PREFIX}/institutions")
        assert resp.status_code == 401

    @patch("app.services.connect_service._build_provider")
    def test_institutions_ok(self, mock_build, client, user):
        mock_provider = MagicMock()
        mock_provider.list_institutions.return_value = MOCK_INSTITUTIONS
        mock_build.return_value = mock_provider

        resp = client.get(
            f"{API_PREFIX}/institutions?country=PL",
            headers=auth_header(user.id),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["name"] == "Sandbox Bank"

    @patch("app.services.connect_service._build_provider")
    def test_create_requisition(self, mock_build, db_session, client, user):
        mock_provider = MagicMock()
        mock_provider.list_institutions.return_value = MOCK_INSTITUTIONS
        mock_provider.create_requisition.return_value = {
            "id": "req-api-1",
            "link": "https://bank.link/auth",
        }
        mock_build.return_value = mock_provider

        resp = client.post(
            f"{API_PREFIX}/requisitions",
            json={
                "institution_id": "SANDBOX_BANK",
                "redirect_uri": "https://app.example.com/callback",
            },
            headers=auth_header(user.id),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["requisition_id"] == "req-api-1"
        assert data["link"] == "https://bank.link/auth"
        assert data["status"] == "pending"

    @patch("app.services.connect_service._build_provider")
    def test_poll_requisition(self, mock_build, db_session, client, user):
        conn = BankConnection(
            id=uuid.uuid4(),
            user_id=user.id,
            provider=BankProvider.NORDIGEN,
            institution_id="SANDBOX_BANK",
            institution_name="Sandbox Bank",
            external_reference="req-poll",
            status=ConnectionStatus.LINKED,
        )
        db_session.add(conn)
        db_session.commit()

        resp = client.get(
            f"{API_PREFIX}/requisitions/{conn.id}",
            headers=auth_header(user.id),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "linked"
        assert data["requisition_id"] == "req-poll"

    def test_list_connections(self, db_session, client, user):
        conn = BankConnection(
            id=uuid.uuid4(),
            user_id=user.id,
            provider=BankProvider.NORDIGEN,
            institution_id="TEST",
            institution_name="Test Bank",
            external_reference="ref-list",
            status=ConnectionStatus.LINKED,
        )
        db_session.add(conn)
        db_session.commit()

        resp = client.get(
            f"{API_PREFIX}/connections",
            headers=auth_header(user.id),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["institution_name"] == "Test Bank"

    def test_disconnect(self, db_session, client, user):
        conn = BankConnection(
            id=uuid.uuid4(),
            user_id=user.id,
            provider=BankProvider.NORDIGEN,
            institution_id="TEST",
            institution_name="Test Bank",
            external_reference="ref-del",
            status=ConnectionStatus.LINKED,
        )
        db_session.add(conn)
        db_session.commit()

        resp = client.delete(
            f"{API_PREFIX}/connections/{conn.id}",
            headers=auth_header(user.id),
        )
        assert resp.status_code == 204

        db_session.refresh(conn)
        assert conn.status == ConnectionStatus.REVOKED

    def test_disconnect_not_found(self, client, user):
        resp = client.delete(
            f"{API_PREFIX}/connections/{uuid.uuid4()}",
            headers=auth_header(user.id),
        )
        assert resp.status_code == 404


# ------------------------------------------------------------------
# Edge case: dedup on poll
# ------------------------------------------------------------------


class TestPollRequisitionDedup:
    @patch("app.services.connect_service._build_provider")
    def test_existing_accounts_not_recreated(self, mock_build, db_session, user):
        conn = BankConnection(
            id=uuid.uuid4(),
            user_id=user.id,
            provider=BankProvider.NORDIGEN,
            institution_id="SANDBOX_BANK",
            institution_name="Sandbox Bank",
            external_reference="req-dedup",
            status=ConnectionStatus.PENDING,
        )
        db_session.add(conn)
        db_session.commit()

        # Pre-create account with same external_account_id
        acc = Account(
            id=uuid.uuid4(), user_id=user.id, bank_connection_id=conn.id,
            external_account_id="ext-dup-1", display_name="Existing",
            account_type=AccountType.CHECKING, currency="PLN",
        )
        db_session.add(acc)
        db_session.commit()

        mock_provider = MagicMock()
        mock_provider.get_requisition.return_value = {"status": "LN"}
        mock_provider.fetch_accounts.return_value = [
            ProviderAccount(
                external_account_id="ext-dup-1",
                iban="PL999",
                currency="PLN",
                display_name="Existing",
                account_type="checking",
                current_balance=Decimal("100.00"),
                balance_as_of=datetime.now(timezone.utc),
            ),
        ]
        mock_build.return_value = mock_provider

        result = connect_service.poll_requisition(
            db_session, connection_id=conn.id, user_id=user.id,
        )
        assert result["status"] == ConnectionStatus.LINKED
        assert len(result["accounts_created"]) == 0  # no new accounts created
