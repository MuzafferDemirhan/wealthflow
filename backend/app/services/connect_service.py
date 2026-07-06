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
from app.services.providers.enable_banking import EnableBankingAdapter, ProviderError
from app.services.providers.plaid import PlaidAdapter, PlaidProviderError

logger = logging.getLogger(__name__)


class InstitutionNotFoundError(Exception):
    pass


class RequisitionNotFoundError(Exception):
    pass


class ConnectionNotFoundError(Exception):
    pass


class ConnectError(Exception):
    pass


# ---------------------------------------------------------------------------
# EnableBanking provider helpers
# ---------------------------------------------------------------------------

def _build_provider() -> EnableBankingAdapter:
    return EnableBankingAdapter(
        app_id=settings.ENABLE_BANKING_APP_ID,
        private_key_pem=settings.ENABLE_BANKING_PRIVATE_KEY,
    )


_ENABLE_STATUS_MAP = {
    "AUTHORIZED": ConnectionStatus.LINKED,
    "EXPIRED": ConnectionStatus.EXPIRED,
    "REVOKED": ConnectionStatus.REVOKED,
}


def _normalise_status(eb_status: str) -> ConnectionStatus:
    return _ENABLE_STATUS_MAP.get(eb_status, ConnectionStatus.PENDING)


def list_institutions(country: str = "PL") -> list[dict]:
    try:
        provider = _build_provider()
        raw = provider.list_institutions(country=country)
    except ProviderError as exc:
        raise ConnectError(f"Failed to fetch institutions: {exc}") from exc

    result = []
    for inst in raw:
        inst_id = f"{inst.get('name', '')}|{country}"
        result.append({
            "id": inst_id,
            "name": inst.get("name", ""),
            "logo": inst.get("logo_url"),
            "country": country,
        })
    result.sort(key=lambda x: x["name"])
    return result


def create_requisition(
    db: Session,
    *,
    user_id: uuid.UUID,
    institution_id: str,
    redirect_uri: str,
) -> dict:
    parts = institution_id.split("|")
    inst_name = parts[0]
    country = parts[1] if len(parts) > 1 else "PL"

    # Validate institution exists before touching DB
    try:
        provider = _build_provider()
        institutions = provider.list_institutions(country=country)
    except ProviderError as exc:
        raise ConnectError(f"Failed to fetch institutions: {exc}") from exc

    known_names = {inst.get("name", "") for inst in institutions}
    if inst_name not in known_names:
        raise InstitutionNotFoundError(f"Institution '{inst_name}' not found in {country}")

    reference = str(uuid.uuid4())
    try:
        req = provider.create_requisition(
            institution_id=institution_id,
            redirect_uri=redirect_uri,
            reference=reference,
        )
    except ProviderError as exc:
        raise ConnectError(f"Failed to create requisition: {exc}") from exc

    authorization_id = req.get("authorization_id", "")
    link = req.get("url", "")

    conn = BankConnection(
        user_id=user_id,
        provider=BankProvider.ENABLE_BANKING,
        institution_id=institution_id,
        institution_name=inst_name,
        external_reference=str(authorization_id),
        status=ConnectionStatus.PENDING,
    )
    db.add(conn)
    db.commit()
    db.refresh(conn)

    return {
        "id": conn.id,
        "requisition_id": authorization_id,
        "link": link,
        "status": ConnectionStatus.PENDING,
        "state": reference,
    }


def authorize_requisition(
    db: Session,
    *,
    connection_id: uuid.UUID,
    user_id: uuid.UUID,
    code: str,
) -> dict:
    conn = db.scalar(
        select(BankConnection).where(
            BankConnection.id == connection_id,
            BankConnection.user_id == user_id,
        )
    )
    if conn is None:
        raise RequisitionNotFoundError()

    try:
        provider = _build_provider()
        session = provider.authorize_session(code)
    except ProviderError as exc:
        raise ConnectError(f"Failed to authorize session: {exc}") from exc

    session_id = session.get("session_id", "")
    if session_id:
        conn.external_reference = session_id

    eb_status = session.get("status", "AUTHORIZED")
    new_status = _normalise_status(eb_status)
    conn.status = new_status
    db.add(conn)
    db.commit()

    accounts_created: list[uuid.UUID] = []
    if new_status == ConnectionStatus.LINKED:
        accounts_created = _sync_provider_accounts(db, conn, provider)

    return {
        "id": conn.id,
        "requisition_id": session_id,
        "status": conn.status,
        "institution_id": conn.institution_id,
        "institution_name": conn.institution_name,
        "accounts_created": accounts_created,
    }


def poll_requisition(
    db: Session,
    *,
    connection_id: uuid.UUID,
    user_id: uuid.UUID,
) -> dict:
    conn = db.scalar(
        select(BankConnection).where(
            BankConnection.id == connection_id,
            BankConnection.user_id == user_id,
        )
    )
    if conn is None:
        raise RequisitionNotFoundError()

    if conn.status == ConnectionStatus.LINKED:
        return {
            "id": conn.id,
            "requisition_id": conn.external_reference,
            "status": conn.status,
            "institution_id": conn.institution_id,
            "institution_name": conn.institution_name,
            "accounts_created": [acc.id for acc in conn.accounts],
        }

    try:
        provider = _build_provider()
        req = provider.get_requisition(conn.external_reference)
    except ProviderError as exc:
        raise ConnectError(f"Failed to poll requisition: {exc}") from exc

    eb_status = req.get("status", "")
    new_status = _normalise_status(eb_status)

    if new_status != conn.status:
        conn.status = new_status
        db.add(conn)
        db.commit()
        db.refresh(conn)

    accounts_created: list[uuid.UUID] = []
    if new_status == ConnectionStatus.LINKED:
        accounts_created = _sync_provider_accounts(db, conn, provider)

    return {
        "id": conn.id,
        "requisition_id": conn.external_reference,
        "status": conn.status,
        "institution_id": conn.institution_id,
        "institution_name": conn.institution_name,
        "accounts_created": accounts_created,
    }


def _sync_provider_accounts(
    db: Session,
    conn: BankConnection,
    provider: EnableBankingAdapter,
) -> list[uuid.UUID]:
    created: list[uuid.UUID] = []
    try:
        provider_accounts = provider.fetch_accounts(conn.external_reference)
    except ProviderError:
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
    stmt = select(BankConnection).where(
        BankConnection.id == connection_id,
        BankConnection.user_id == user_id,
    )
    conn = db.scalar(stmt)
    if conn is None:
        raise ConnectionNotFoundError()

    # Revoke at provider level
    if conn.provider == BankProvider.PLAID:
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
