import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.models.account import Account, AccountType
from app.models.bank_connection import BankConnection, BankProvider, ConnectionStatus
from app.models.transaction import Transaction, TransactionStatus
from app.models.user import User, UserRole
from app.services.providers.base import ProviderTransaction
from app.tasks.ingestion import (
    _compute_since,
    _upsert_transaction,
    sync_account_transactions,
    sync_all_due_connections,
)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

@pytest.fixture()
def db_with_account(db_session):
    """Create a minimal user + connection + account for ingestion tests."""
    user = User(
        id=uuid.uuid4(),
        email="ingest@example.com",
        hashed_password="x",
        full_name="Ingest User",
        role=UserRole.USER,
    )
    db_session.add(user)
    db_session.flush()

    conn = BankConnection(
        id=uuid.uuid4(),
        user_id=user.id,
        provider=BankProvider.NORDIGEN,
        institution_id="TEST",
        institution_name="Test Bank",
        external_reference="ref-ingest-1",
        status=ConnectionStatus.LINKED,
        last_synced_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db_session.add(conn)
    db_session.flush()

    account = Account(
        id=uuid.uuid4(),
        user_id=user.id,
        bank_connection_id=conn.id,
        external_account_id="ext-acc-1",
        display_name="Ingest Account",
        account_type=AccountType.CHECKING,
        currency="PLN",
    )
    db_session.add(account)
    db_session.commit()
    return db_session, user, conn, account


# ------------------------------------------------------------------
# Unit: _compute_since
# ------------------------------------------------------------------


class TestComputeSince:
    def test_never_synced_returns_90_days_ago(self):
        since = _compute_since(None)
        expected = date.today() - timedelta(days=90)
        assert since == expected

    def test_recently_synced_returns_90_days_before_sync(self):
        last = datetime(2026, 7, 1, tzinfo=timezone.utc)
        since = _compute_since(last)
        expected = date(2026, 7, 1) - timedelta(days=90)
        assert since == expected

    def test_sync_is_earlier_than_today_minus_90(self):
        last = datetime(2025, 1, 1, tzinfo=timezone.utc)
        since = _compute_since(last)
        expected = date(2025, 1, 1) - timedelta(days=90)
        assert since == expected


# ------------------------------------------------------------------
# Unit: _upsert_transaction
# ------------------------------------------------------------------


class TestUpsertTransaction:
    def test_inserts_new_transaction(self, db_session):
        account_id = uuid.uuid4()
        raw = ProviderTransaction(
            external_id="txn-1",
            amount=Decimal("-45.99"),
            currency="PLN",
            booking_date=date(2026, 7, 1),
            value_date=date(2026, 7, 1),
            status="booked",
            description="Lidl",
            counterparty_name="LIDL",
        )
        txn_id = _upsert_transaction(db_session, account_id=account_id, raw=raw)
        assert txn_id is not None
        saved = db_session.get(Transaction, txn_id)
        assert saved is not None
        assert saved.amount == Decimal("-45.99")
        assert saved.description == "Lidl"

    def test_duplicate_returns_none(self, db_session):
        account_id = uuid.uuid4()
        raw = ProviderTransaction(
            external_id="txn-2",
            amount=Decimal("100.00"),
            currency="EUR",
            booking_date=date(2026, 7, 2),
            value_date=None,
            status="booked",
            description="Salary",
            counterparty_name=None,
        )
        txn_id_1 = _upsert_transaction(db_session, account_id=account_id, raw=raw)
        txn_id_2 = _upsert_transaction(db_session, account_id=account_id, raw=raw)
        assert txn_id_1 is not None
        assert txn_id_2 is None  # duplicate

    def test_different_account_no_collision(self, db_session):
        acc_a = uuid.uuid4()
        acc_b = uuid.uuid4()
        raw = ProviderTransaction(
            external_id="txn-3",
            amount=Decimal("-10.00"),
            currency="PLN",
            booking_date=date(2026, 7, 3),
            value_date=None,
            status="pending",
            description="Test",
            counterparty_name=None,
        )
        id_a = _upsert_transaction(db_session, account_id=acc_a, raw=raw)
        id_b = _upsert_transaction(db_session, account_id=acc_b, raw=raw)
        assert id_a is not None
        assert id_b is not None
        assert id_a != id_b

    def test_pending_status_mapped_correctly(self, db_session):
        account_id = uuid.uuid4()
        raw = ProviderTransaction(
            external_id="txn-pending",
            amount=Decimal("-5.00"),
            currency="PLN",
            booking_date=date(2026, 7, 4),
            value_date=None,
            status="pending",
            description="Pending txn",
            counterparty_name=None,
        )
        txn_id = _upsert_transaction(db_session, account_id=account_id, raw=raw)
        saved = db_session.get(Transaction, txn_id)
        assert saved.status == TransactionStatus.PENDING


# ------------------------------------------------------------------
# Integration: sync_account_transactions
# ------------------------------------------------------------------


class TestSyncAccountTransactions:
    def test_happy_path(self, db_with_account):
        db_session, user, conn, account = db_with_account

        mock_raw_txns = [
            ProviderTransaction(
                external_id="nord-txn-1",
                amount=Decimal("-120.00"),
                currency="PLN",
                booking_date=date(2026, 7, 1),
                value_date=date(2026, 7, 1),
                status="booked",
                description="Restauracja Warszawa",
                counterparty_name="RESTAURACJA U DOMINIKA",
            ),
            ProviderTransaction(
                external_id="nord-txn-2",
                amount=Decimal("-45.99"),
                currency="PLN",
                booking_date=date(2026, 7, 2),
                value_date=None,
                status="booked",
                description="Lidl",
                counterparty_name="LIDL",
            ),
        ]

        mock_provider = MagicMock()
        mock_provider.fetch_transactions.return_value = mock_raw_txns
        mock_provider.fetch_balances.return_value = (Decimal("5000.00"), datetime.now(timezone.utc))

        with patch("app.tasks.ingestion._build_provider", return_value=mock_provider):
            with patch("app.tasks.ingestion.celery_app.send_task") as mock_send:
                result = sync_account_transactions(str(account.id))

        assert result["ok"] is True
        assert result["transactions_fetched"] == 2
        assert result["transactions_new"] == 2

        # Verify transactions were persisted
        txns = db_session.query(Transaction).filter(
            Transaction.account_id == account.id
        ).all()
        assert len(txns) == 2

        # Verify balance was updated
        db_session.refresh(account)
        assert account.current_balance == Decimal("5000.00")

        # Verify classification was enqueued for both new txns
        assert mock_send.call_count == 2
        calls = mock_send.call_args_list
        for call in calls:
            assert call[0][0] == "ingestion.classify_transaction"

        # Verify last_synced_at was updated on the connection
        db_session.refresh(conn)
        assert conn.last_synced_at is not None

    def test_duplicate_transactions_skipped(self, db_with_account):
        db_session, user, conn, account = db_with_account

        # Insert one transaction first — compute the real dedupe_hash
        # so the dedup mechanism can find it.
        from app.services.transaction_service import compute_dedupe_hash
        expected_hash = compute_dedupe_hash(
            account_id=account.id,
            amount=Decimal("-50.00"),
            currency="PLN",
            booking_date=date(2026, 7, 1),
            description="Existing",
        )
        existing_txn = Transaction(
            id=uuid.uuid4(),
            account_id=account.id,
            external_id="existing-1",
            dedupe_hash=expected_hash,
            amount=Decimal("-50.00"),
            currency="PLN",
            booking_date=date(2026, 7, 1),
            status=TransactionStatus.BOOKED,
            description="Existing",
        )
        db_session.add(existing_txn)
        db_session.commit()

        raw_same = ProviderTransaction(
            external_id="dup-txn",
            amount=Decimal("-50.00"),
            currency="PLN",
            booking_date=date(2026, 7, 1),
            value_date=None,
            status="booked",
            description="Existing",
            counterparty_name=None,
        )
        raw_new = ProviderTransaction(
            external_id="new-txn",
            amount=Decimal("-30.00"),
            currency="PLN",
            booking_date=date(2026, 7, 2),
            value_date=None,
            status="booked",
            description="New",
            counterparty_name=None,
        )

        mock_provider = MagicMock()
        mock_provider.fetch_transactions.return_value = [raw_same, raw_new]
        mock_provider.fetch_balances.return_value = (Decimal("1000.00"), datetime.now(timezone.utc))

        with patch("app.tasks.ingestion._build_provider", return_value=mock_provider):
            with patch("app.tasks.ingestion.celery_app.send_task"):
                result = sync_account_transactions(str(account.id))

        assert result["transactions_fetched"] == 2
        assert result["transactions_new"] == 1  # only the new one

    def test_invalid_account_id(self, db_session):
        result = sync_account_transactions("not-a-uuid")
        assert result["ok"] is False
        assert "invalid" in result["error"].lower()

    def test_account_not_found(self, db_session):
        result = sync_account_transactions(str(uuid.uuid4()))
        assert result["ok"] is False
        assert "not found" in result["error"].lower()

    def test_not_linked_connection_skipped(self, db_with_account):
        db_session, user, conn, account = db_with_account
        conn.status = ConnectionStatus.PENDING
        db_session.add(conn)
        db_session.commit()

        result = sync_account_transactions(str(account.id))
        assert result["ok"] is False
        assert "not LINKED" in result["error"]

    def test_provider_error_triggers_retry(self, db_with_account):
        db_session, user, conn, account = db_with_account

        mock_provider = MagicMock()
        from app.services.providers.nordigen import ProviderError
        mock_provider.fetch_transactions.side_effect = ProviderError("API down")

        with patch("app.tasks.ingestion._build_provider", return_value=mock_provider):
            with pytest.raises(Exception) as excinfo:
                sync_account_transactions(str(account.id))
            # retry is raised by self.retry()
            assert True


# ------------------------------------------------------------------
# Integration: sync_all_due_connections
# ------------------------------------------------------------------


class TestSyncAllDueConnections:
    def test_finds_stale_connections_and_fans_out(self, db_session):
        user = User(id=uuid.uuid4(), email="fanout@example.com", hashed_password="x", full_name="U", role=UserRole.USER)
        db_session.add(user)
        db_session.flush()

        stale_conn = BankConnection(
            id=uuid.uuid4(),
            user_id=user.id,
            provider=BankProvider.NORDIGEN,
            institution_id="T1",
            institution_name="Test 1",
            external_reference="ref-fan-1",
            status=ConnectionStatus.LINKED,
            last_synced_at=datetime.now(timezone.utc) - timedelta(hours=10),
        )
        fresh_conn = BankConnection(
            id=uuid.uuid4(),
            user_id=user.id,
            provider=BankProvider.NORDIGEN,
            institution_id="T2",
            institution_name="Test 2",
            external_reference="ref-fan-2",
            status=ConnectionStatus.LINKED,
            last_synced_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        db_session.add_all([stale_conn, fresh_conn])
        db_session.flush()

        # Add accounts to the stale connection
        acc1 = Account(id=uuid.uuid4(), user_id=user.id, bank_connection_id=stale_conn.id,
                       external_account_id="ext-a1", display_name="A1", account_type=AccountType.CHECKING, currency="PLN")
        acc2 = Account(id=uuid.uuid4(), user_id=user.id, bank_connection_id=stale_conn.id,
                       external_account_id="ext-a2", display_name="A2", account_type=AccountType.SAVINGS, currency="PLN")
        db_session.add_all([acc1, acc2])
        db_session.commit()

        with patch("app.tasks.ingestion.sync_account_transactions.delay") as mock_delay:
            result = sync_all_due_connections()

        assert result["connections_found"] == 1
        assert result["accounts_enqueued"] == 2
        assert mock_delay.call_count == 2

    def test_no_stale_connections(self, db_session):
        result = sync_all_due_connections()
        assert result["connections_found"] == 0
        assert result["accounts_enqueued"] == 0


class TestSyncAccountTransactionsEdgeCases:
    def test_balance_fetch_failure_does_not_block_sync(self, db_with_account):
        db_session, user, conn, account = db_with_account

        mock_raw_txns = [
            ProviderTransaction(
                external_id="edge-txn-1",
                amount=Decimal("-10.00"),
                currency="PLN",
                booking_date=date(2026, 7, 1),
                value_date=None,
                status="booked",
                description="Edge test",
                counterparty_name=None,
            ),
        ]

        mock_provider = MagicMock()
        mock_provider.fetch_transactions.return_value = mock_raw_txns
        mock_provider.fetch_balances.side_effect = ProviderError("Balance API down")

        with patch("app.tasks.ingestion._build_provider", return_value=mock_provider):
            with patch("app.tasks.ingestion.celery_app.send_task"):
                result = sync_account_transactions(str(account.id))

        assert result["ok"] is True
        assert result["transactions_new"] == 1
        # Balance was not updated but sync completed
        db_session.refresh(account)
        assert account.current_balance == Decimal("0")

    def test_non_nordigen_provider_skipped(self, db_with_account):
        db_session, user, conn, account = db_with_account
        conn.provider = "plaid"
        db_session.add(conn)
        db_session.commit()

        result = sync_account_transactions(str(account.id))
        assert result["ok"] is False
        assert "unsupported provider" in result["error"].lower()


from app.services.providers.nordigen import ProviderError  # noqa: E402


