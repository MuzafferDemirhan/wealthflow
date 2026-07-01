import uuid
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.holding import AssetType, Holding


class HoldingNotFoundError(Exception):
    pass


def get_user_holdings(db: Session, *, user_id: uuid.UUID) -> list[Holding]:
    stmt = (
        select(Holding)
        .where(Holding.user_id == user_id)
        .order_by(Holding.symbol.asc())
    )
    return list(db.scalars(stmt).all())


def get_holding(db: Session, *, holding_id: uuid.UUID, user_id: uuid.UUID) -> Holding:
    stmt = select(Holding).where(Holding.id == holding_id, Holding.user_id == user_id)
    holding = db.scalar(stmt)
    if holding is None:
        raise HoldingNotFoundError()
    return holding


def create_holding(
    db: Session,
    *,
    user_id: uuid.UUID,
    symbol: str,
    name: str,
    asset_type: AssetType,
    currency: str,
    quantity: Decimal,
    cost_basis: Optional[Decimal] = None,
    current_price: Optional[Decimal] = None,
    as_of_date: Optional[date] = None,
    account_id: Optional[uuid.UUID] = None,
    notes: Optional[str] = None,
) -> Holding:
    holding = Holding(
        user_id=user_id,
        account_id=account_id,
        symbol=symbol.upper(),
        name=name,
        asset_type=asset_type,
        currency=currency.upper(),
        quantity=quantity,
        cost_basis=cost_basis,
        current_price=current_price,
        as_of_date=as_of_date,
        notes=notes,
    )
    db.add(holding)
    db.commit()
    db.refresh(holding)
    return holding


def update_holding(
    db: Session,
    *,
    holding_id: uuid.UUID,
    user_id: uuid.UUID,
    symbol: Optional[str] = None,
    name: Optional[str] = None,
    asset_type: Optional[AssetType] = None,
    currency: Optional[str] = None,
    quantity: Optional[Decimal] = None,
    cost_basis: Optional[Decimal] = None,
    current_price: Optional[Decimal] = None,
    as_of_date: Optional[date] = None,
    account_id: Optional[uuid.UUID] = None,
    notes: Optional[str] = None,
) -> Holding:
    holding = get_holding(db, holding_id=holding_id, user_id=user_id)

    if symbol is not None:
        holding.symbol = symbol.upper()
    if name is not None:
        holding.name = name
    if asset_type is not None:
        holding.asset_type = asset_type
    if currency is not None:
        holding.currency = currency.upper()
    if quantity is not None:
        holding.quantity = quantity
    if cost_basis is not None:
        holding.cost_basis = cost_basis
    if current_price is not None:
        holding.current_price = current_price
    if as_of_date is not None:
        holding.as_of_date = as_of_date
    if account_id is not None:
        holding.account_id = account_id
    if notes is not None:
        holding.notes = notes

    db.add(holding)
    db.commit()
    db.refresh(holding)
    return holding


def delete_holding(db: Session, *, holding_id: uuid.UUID, user_id: uuid.UUID) -> None:
    holding = get_holding(db, holding_id=holding_id, user_id=user_id)
    db.delete(holding)
    db.commit()


def compute_summary(db: Session, *, user_id: uuid.UUID) -> dict:
    holdings = get_user_holdings(db, user_id=user_id)

    total_market_value = Decimal("0")
    total_cost_basis = Decimal("0")
    has_cost_basis = False
    allocation: dict[str, Decimal] = {}

    for h in holdings:
        mv = (h.quantity * h.current_price) if h.current_price is not None else Decimal("0")
        total_market_value += mv

        if h.cost_basis is not None:
            total_cost_basis += h.cost_basis
            has_cost_basis = True

        asset_label = h.asset_type.value
        allocation[asset_label] = allocation.get(asset_label, Decimal("0")) + mv

    # Recalculate allocation as percentages (0–100)
    allocation_pct: dict[str, Decimal] = {}
    if total_market_value > 0:
        for key, val in allocation.items():
            allocation_pct[key] = (val / total_market_value * 100).quantize(Decimal("0.01"))

    total_gain_loss = None
    total_gain_loss_pct = None
    if has_cost_basis and total_cost_basis > 0:
        total_gain_loss = total_market_value - total_cost_basis
        total_gain_loss_pct = float((total_gain_loss / total_cost_basis) * 100)

    return {
        "total_market_value": total_market_value,
        "total_cost_basis": total_cost_basis if has_cost_basis else None,
        "total_gain_loss": total_gain_loss,
        "total_gain_loss_pct": total_gain_loss_pct,
        "holdings_count": len(holdings),
        "allocation": dict(sorted(allocation_pct.items())),
    }
