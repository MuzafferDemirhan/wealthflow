import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.holding import AssetType, Holding
from app.models.user import User, UserRole
from app.services.portfolio_service import (
    HoldingNotFoundError,
    compute_summary,
    create_holding,
    delete_holding,
    get_holding,
    get_user_holdings,
    update_holding,
)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

@pytest.fixture()
def user(db_session):
    u = User(
        id=uuid.uuid4(),
        email="portfolio@example.com",
        hashed_password="x",
        full_name="Portfolio User",
        role=UserRole.USER,
    )
    db_session.add(u)
    db_session.commit()
    return u


def auth_header(user_id: uuid.UUID) -> dict:
    """Produce a dummy Bearer token that bypasses real JWT verification.

    The ``get_current_user`` dependency decodes the token via
    ``decode_token`` and reads ``sub`` as the user ID.  For tests we
    forge a token payload that ``decode_token`` will accept — this
    avoids needing to create a real access token for every test.
    """
    import jwt
    from app.core.config import settings
    from app.core.security import ALGORITHM

    token = jwt.encode(
        {"sub": str(user_id), "type": "access"},
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )
    return {"Authorization": f"Bearer {token}"}


# ------------------------------------------------------------------
# Unit: service layer
# ------------------------------------------------------------------


class TestCreateHolding:
    def test_creates_holding(self, db_session, user):
        h = create_holding(
            db_session,
            user_id=user.id,
            symbol="AAPL",
            name="Apple Inc.",
            asset_type=AssetType.STOCK,
            currency="USD",
            quantity=Decimal("10"),
            cost_basis=Decimal("1500.00"),
            current_price=Decimal("198.50"),
            as_of_date=date(2026, 7, 1),
        )
        assert h.symbol == "AAPL"
        assert h.name == "Apple Inc."
        assert h.quantity == Decimal("10")
        assert h.cost_basis == Decimal("1500.00")
        assert h.current_price == Decimal("198.50")
        assert h.user_id == user.id

    def test_symbol_upper_cased(self, db_session, user):
        h = create_holding(
            db_session,
            user_id=user.id,
            symbol="btc",
            name="Bitcoin",
            asset_type=AssetType.CRYPTO,
            currency="USD",
            quantity=Decimal("1"),
        )
        assert h.symbol == "BTC"


class TestGetUserHoldings:
    def test_returns_user_holdings(self, db_session, user):
        create_holding(
            db_session, user_id=user.id, symbol="AAPL", name="Apple",
            asset_type=AssetType.STOCK, currency="USD", quantity=Decimal("5"),
        )
        create_holding(
            db_session, user_id=user.id, symbol="GOOGL", name="Alphabet",
            asset_type=AssetType.STOCK, currency="USD", quantity=Decimal("3"),
        )
        holdings = get_user_holdings(db_session, user_id=user.id)
        assert len(holdings) == 2

    def test_other_user_not_included(self, db_session, user):
        other_user = User(
            id=uuid.uuid4(), email="other@example.com",
            hashed_password="x", full_name="Other", role=UserRole.USER,
        )
        db_session.add(other_user)
        db_session.commit()

        create_holding(
            db_session, user_id=other_user.id, symbol="TSLA", name="Tesla",
            asset_type=AssetType.STOCK, currency="USD", quantity=Decimal("1"),
        )
        holdings = get_user_holdings(db_session, user_id=user.id)
        assert len(holdings) == 0


class TestGetHolding:
    def test_found(self, db_session, user):
        h = create_holding(
            db_session, user_id=user.id, symbol="MSFT", name="Microsoft",
            asset_type=AssetType.STOCK, currency="USD", quantity=Decimal("2"),
        )
        fetched = get_holding(db_session, holding_id=h.id, user_id=user.id)
        assert fetched.id == h.id

    def test_not_found_raises(self, db_session, user):
        with pytest.raises(HoldingNotFoundError):
            get_holding(db_session, holding_id=uuid.uuid4(), user_id=user.id)

    def test_wrong_user_raises(self, db_session, user):
        other_user = User(
            id=uuid.uuid4(), email="other2@example.com",
            hashed_password="x", full_name="Other2", role=UserRole.USER,
        )
        db_session.add(other_user)
        db_session.commit()

        h = create_holding(
            db_session, user_id=user.id, symbol="AMZN", name="Amazon",
            asset_type=AssetType.STOCK, currency="USD", quantity=Decimal("1"),
        )
        with pytest.raises(HoldingNotFoundError):
            get_holding(db_session, holding_id=h.id, user_id=other_user.id)


class TestUpdateHolding:
    def test_updates_fields(self, db_session, user):
        h = create_holding(
            db_session, user_id=user.id, symbol="NVDA", name="NVIDIA",
            asset_type=AssetType.STOCK, currency="USD", quantity=Decimal("1"),
            current_price=Decimal("100.00"),
        )
        updated = update_holding(
            db_session,
            holding_id=h.id,
            user_id=user.id,
            quantity=Decimal("5"),
            current_price=Decimal("120.00"),
            notes="Added more shares",
        )
        assert updated.quantity == Decimal("5")
        assert updated.current_price == Decimal("120.00")
        assert updated.notes == "Added more shares"

    def test_not_found_raises(self, db_session, user):
        with pytest.raises(HoldingNotFoundError):
            update_holding(
                db_session,
                holding_id=uuid.uuid4(),
                user_id=user.id,
                quantity=Decimal("1"),
            )


class TestDeleteHolding:
    def test_deletes(self, db_session, user):
        h = create_holding(
            db_session, user_id=user.id, symbol="ETH", name="Ethereum",
            asset_type=AssetType.CRYPTO, currency="USD", quantity=Decimal("2"),
        )
        delete_holding(db_session, holding_id=h.id, user_id=user.id)
        with pytest.raises(HoldingNotFoundError):
            get_holding(db_session, holding_id=h.id, user_id=user.id)

    def test_not_found_raises(self, db_session, user):
        with pytest.raises(HoldingNotFoundError):
            delete_holding(db_session, holding_id=uuid.uuid4(), user_id=user.id)


class TestComputeSummary:
    def test_empty_portfolio(self, db_session, user):
        summary = compute_summary(db_session, user_id=user.id)
        assert summary["holdings_count"] == 0
        assert summary["total_market_value"] == Decimal("0")
        assert summary["total_cost_basis"] is None

    def test_single_holding(self, db_session, user):
        create_holding(
            db_session, user_id=user.id, symbol="AAPL", name="Apple",
            asset_type=AssetType.STOCK, currency="USD",
            quantity=Decimal("10"), current_price=Decimal("200.00"),
            cost_basis=Decimal("1500.00"),
        )
        summary = compute_summary(db_session, user_id=user.id)
        assert summary["holdings_count"] == 1
        assert summary["total_market_value"] == Decimal("2000.00")
        assert summary["total_cost_basis"] == Decimal("1500.00")
        assert summary["total_gain_loss"] == Decimal("500.00")
        assert summary["allocation"] == {"stock": Decimal("100.00")}

    def test_multi_asset_allocation(self, db_session, user):
        create_holding(
            db_session, user_id=user.id, symbol="AAPL", name="Apple",
            asset_type=AssetType.STOCK, currency="USD",
            quantity=Decimal("10"), current_price=Decimal("150.00"),
        )
        create_holding(
            db_session, user_id=user.id, symbol="BTC", name="Bitcoin",
            asset_type=AssetType.CRYPTO, currency="USD",
            quantity=Decimal("1"), current_price=Decimal("50000.00"),
            cost_basis=Decimal("45000.00"),
        )
        summary = compute_summary(db_session, user_id=user.id)
        assert summary["holdings_count"] == 2
        expected_total = Decimal("1500.00") + Decimal("50000.00")
        assert summary["total_market_value"] == expected_total
        assert summary["total_cost_basis"] == Decimal("45000.00")
        assert summary["total_gain_loss"] == expected_total - Decimal("45000.00")
        assert summary["allocation"]["stock"] == Decimal("2.91")
        assert summary["allocation"]["crypto"] == Decimal("97.09")

    def test_no_cost_basis(self, db_session, user):
        create_holding(
            db_session, user_id=user.id, symbol="AAPL", name="Apple",
            asset_type=AssetType.STOCK, currency="USD",
            quantity=Decimal("10"), current_price=Decimal("200.00"),
        )
        summary = compute_summary(db_session, user_id=user.id)
        assert summary["total_cost_basis"] is None
        assert summary["total_gain_loss"] is None
        assert summary["total_gain_loss_pct"] is None

    def test_only_other_user_holdings_ignored(self, db_session, user):
        other_user = User(
            id=uuid.uuid4(), email="other3@example.com",
            hashed_password="x", full_name="Other3", role=UserRole.USER,
        )
        db_session.add(other_user)
        db_session.commit()
        create_holding(
            db_session, user_id=other_user.id, symbol="TSLA", name="Tesla",
            asset_type=AssetType.STOCK, currency="USD",
            quantity=Decimal("5"), current_price=Decimal("300.00"),
        )
        summary = compute_summary(db_session, user_id=user.id)
        assert summary["holdings_count"] == 0
        assert summary["total_market_value"] == Decimal("0")


# ------------------------------------------------------------------
# Integration: portfolio API endpoints
# ------------------------------------------------------------------

API_PREFIX = "/api/v1/portfolio"


class TestHoldingAPI:
    def test_list_empty(self, db_session, client, user):
        response = client.get(f"{API_PREFIX}/holdings", headers=auth_header(user.id))
        assert response.status_code == 200
        assert response.json() == []

    def test_create_and_list(self, db_session, client, user):
        payload = {
            "symbol": "AAPL",
            "name": "Apple Inc.",
            "asset_type": "stock",
            "currency": "USD",
            "quantity": "10",
            "cost_basis": "1500.00",
            "current_price": "198.50",
        }
        resp = client.post(
            f"{API_PREFIX}/holdings",
            json=payload,
            headers=auth_header(user.id),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["symbol"] == "AAPL"
        assert Decimal(data["quantity"]) == Decimal("10")
        assert Decimal(data["cost_basis"]) == Decimal("1500.00")
        assert Decimal(data["current_price"]) == Decimal("198.50")
        assert "id" in data

        # list
        resp2 = client.get(f"{API_PREFIX}/holdings", headers=auth_header(user.id))
        assert len(resp2.json()) == 1

    def test_get_single(self, db_session, client, user):
        # create first
        create_holding(
            db_session, user_id=user.id, symbol="GOOGL", name="Alphabet",
            asset_type=AssetType.STOCK, currency="USD", quantity=Decimal("3"),
        )
        stmt = select(Holding).where(Holding.user_id == user.id)
        holding = db_session.scalar(stmt)

        resp = client.get(
            f"{API_PREFIX}/holdings/{holding.id}",
            headers=auth_header(user.id),
        )
        assert resp.status_code == 200
        assert resp.json()["symbol"] == "GOOGL"

    def test_get_not_found(self, db_session, client, user):
        resp = client.get(
            f"{API_PREFIX}/holdings/{uuid.uuid4()}",
            headers=auth_header(user.id),
        )
        assert resp.status_code == 404

    def test_update(self, db_session, client, user):
        create_holding(
            db_session, user_id=user.id, symbol="NVDA", name="NVIDIA",
            asset_type=AssetType.STOCK, currency="USD",
            quantity=Decimal("1"), current_price=Decimal("100.00"),
        )
        stmt = select(Holding).where(Holding.user_id == user.id)
        holding = db_session.scalar(stmt)

        resp = client.put(
            f"{API_PREFIX}/holdings/{holding.id}",
            json={"quantity": "5", "notes": "Added more"},
            headers=auth_header(user.id),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert Decimal(data["quantity"]) == Decimal("5")
        assert data["notes"] == "Added more"

    def test_delete(self, db_session, client, user):
        create_holding(
            db_session, user_id=user.id, symbol="ETH", name="Ethereum",
            asset_type=AssetType.CRYPTO, currency="USD", quantity=Decimal("2"),
        )
        stmt = select(Holding).where(Holding.user_id == user.id)
        holding = db_session.scalar(stmt)

        resp = client.delete(
            f"{API_PREFIX}/holdings/{holding.id}",
            headers=auth_header(user.id),
        )
        assert resp.status_code == 204

        # verify gone
        resp2 = client.get(
            f"{API_PREFIX}/holdings/{holding.id}",
            headers=auth_header(user.id),
        )
        assert resp2.status_code == 404

    def test_summary(self, db_session, client, user):
        create_holding(
            db_session, user_id=user.id, symbol="AAPL", name="Apple",
            asset_type=AssetType.STOCK, currency="USD",
            quantity=Decimal("10"), current_price=Decimal("200.00"),
            cost_basis=Decimal("1500.00"),
        )
        resp = client.get(f"{API_PREFIX}/summary", headers=auth_header(user.id))
        assert resp.status_code == 200
        data = resp.json()
        assert data["holdings_count"] == 1
        assert Decimal(data["total_market_value"]) == Decimal("2000.00")
        assert Decimal(data["total_gain_loss"]) == Decimal("500.00")

    def test_unauthorized(self, db_session, client):
        resp = client.get(f"{API_PREFIX}/holdings")
        assert resp.status_code == 401
