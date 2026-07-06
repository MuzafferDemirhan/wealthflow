import logging
import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.encryption import decrypt_token as _decrypt_token
from app.core.encryption import encrypt_token as _encrypt_token
from app.models.account import Account, AccountType
from app.models.bank_connection import BankConnection, BankProvider, ConnectionStatus
from app.services.providers.plaid import PlaidAdapter, PlaidProviderError

logger = logging.getLogger(__name__)


class ConnectionNotFoundError(Exception):
    pass


class ConnectError(Exception):
    pass


# ---------------------------------------------------------------------------
# Plaid provider
# ---------------------------------------------------------------------------

def _build_plaid_provider() -> PlaidAdapter:
    return PlaidAdapter(
        client_id=settings.PLAID_CLIENT_ID,
        secret=settings.PLAID_SECRET,
        env=settings.PLAID_ENV,
        products=settings.PLAID_PRODUCTS,
        country_codes=settings.PLAID_COUNTRY_CODES,
    )


def create_plaid_link_token(
    *,
    user_id: uuid.UUID,
    redirect_uri: Optional[str] = None,
) -> dict:
    """
    Step 1 of Plaid Link: create a link_token for the frontend SDK.
    Returns {"link_token": "..."}.
    """
    try:
        provider = _build_plaid_provider()
        link_token = provider.create_link_token(
            user_id=str(user_id),
            redirect_uri=redirect_uri,
        )
    except PlaidProviderError as exc:
        raise ConnectError(f"Failed to create Plaid link token: {exc}") from exc
    return {"link_token": link_token}


def exchange_plaid_public_token(
    db: Session,
    *,
    user_id: uuid.UUID,
    public_token: str,
    institution_id: str,
    institution_name: str,
) -> dict:
    """
    Step 2 of Plaid Link: exchange public_token -> access_token.
    Stores access_token ENCRYPTED in BankConnection.external_reference.
    Creates accounts immediately (Plaid is synchronous after exchange).
    """
    try:
        provider = _build_plaid_provider()
        access_token, item_id = provider.exchange_public_token(public_token)
    except PlaidProviderError as exc:
        raise ConnectError(f"Plaid token exchange failed: {exc}") from exc

    encrypted_token = _encrypt_token(access_token)

    conn = BankConnection(
        user_id=user_id,
        provider=BankProvider.PLAID,
        institution_id=institution_id,
        institution_name=institution_name,
        external_reference=encrypted_token,
        status=ConnectionStatus.LINKED,
    )
    db.add(conn)
    db.commit()
    db.refresh(conn)

    accounts_created = _sync_plaid_accounts(db, conn, provider, access_token)

    for account_id in accounts_created:
        celery_app.send_task(
            "ingestion.sync_account_transactions",
            args=[str(account_id)],
        )

    return {
        "id": conn.id,
        "status": conn.status.value if conn.status else "",
        "institution_id": conn.institution_id,
        "institution_name": conn.institution_name,
        "accounts_created": accounts_created,
        "item_id": item_id,
    }


def _sync_plaid_accounts(
    db: Session,
    conn: BankConnection,
    provider: PlaidAdapter,
    access_token: str,
) -> list[uuid.UUID]:
    """Fetch Plaid accounts and create Account rows."""
    created: list[uuid.UUID] = []
    try:
        provider_accounts = provider.fetch_accounts(access_token)
    except PlaidProviderError:
        logger.exception("Failed to fetch Plaid accounts for connection %s", conn.id)
        return created

    for pa in provider_accounts:
        existing = db.scalar(
            select(Account).where(
                Account.external_account_id == pa.external_account_id,
                Account.user_id == conn.user_id,
            )
        )
        if existing is not None:
            continue

        try:
            atype = AccountType(pa.account_type)
        except ValueError:
            atype = AccountType.OTHER

        acc = Account(
            user_id=conn.user_id,
            bank_connection_id=conn.id,
            external_account_id=pa.external_account_id,
            display_name=pa.display_name,
            account_type=atype,
            iban=pa.iban,
            currency=pa.currency,
            current_balance=pa.current_balance,
            balance_as_of=pa.balance_as_of,
        )
        db.add(acc)
        db.flush()
        created.append(acc.id)

    if created:
        db.commit()
    return created


def get_user_connections(db: Session, *, user_id: uuid.UUID) -> list[BankConnection]:
    stmt = (
        select(BankConnection)
        .where(BankConnection.user_id == user_id)
        .order_by(BankConnection.created_at.desc())
    )
    return list(db.scalars(stmt).all())


def disconnect_connection(
    db: Session, *, connection_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    conn = db.scalar(
        select(BankConnection).where(
            BankConnection.id == connection_id,
            BankConnection.user_id == user_id,
        )
    )
    if conn is None:
        raise ConnectionNotFoundError()

    # Revoke Plaid item at provider level
    try:
        provider = _build_plaid_provider()
        access_token = _decrypt_token(conn.external_reference)
        provider.revoke_item(access_token)
    except Exception:
        logger.warning("Failed to revoke Plaid item for connection %s", conn.id)

    accounts = db.scalars(
        select(Account).where(
            Account.bank_connection_id == conn.id,
            Account.user_id == user_id,
        )
    ).all()
    for acc in accounts:
        acc.is_active = False
        db.add(acc)

    conn.status = ConnectionStatus.REVOKED
    db.add(conn)
    db.commit()
