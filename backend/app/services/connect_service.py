import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.models.account import Account, AccountType
from app.models.bank_connection import BankConnection, BankProvider, ConnectionStatus
from app.services.providers.nordigen import NordigenAdapter, ProviderError


class InstitutionNotFoundError(Exception):
    pass


class RequisitionNotFoundError(Exception):
    pass


class ConnectionNotFoundError(Exception):
    pass


class ConnectError(Exception):
    pass


def _build_provider() -> NordigenAdapter:
    return NordigenAdapter(
        secret_id=settings.NORDIGEN_SECRET_ID,
        secret_key=settings.NORDIGEN_SECRET_KEY,
    )


def _normalise_status(nordigen_status: str) -> ConnectionStatus:
    mapping = {
        "CR": ConnectionStatus.PENDING,
        "GC": ConnectionStatus.PENDING,
        "UA": ConnectionStatus.PENDING,
        "GA": ConnectionStatus.PENDING,
        "LN": ConnectionStatus.LINKED,
        "RJ": ConnectionStatus.ERROR,
        "EX": ConnectionStatus.EXPIRED,
        "SA": ConnectionStatus.REVOKED,
    }
    return mapping.get(nordigen_status, ConnectionStatus.ERROR)


def list_institutions(
    country: str = "PL",
) -> list[dict]:
    try:
        provider = _build_provider()
        raw = provider.list_institutions(country=country)
    except ProviderError as exc:
        raise ConnectError(f"Failed to fetch institutions: {exc}") from exc

    result = []
    for inst in raw:
        result.append({
            "id": inst.get("id", ""),
            "name": inst.get("name", ""),
            "logo": inst.get("logo"),
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
    # Look up institution name
    try:
        institutions = _build_provider().list_institutions()
    except ProviderError as exc:
        raise ConnectError(f"Failed to list institutions: {exc}") from exc

    institution_name = None
    for inst in institutions:
        if inst.get("id") == institution_id:
            institution_name = inst.get("name", institution_id)
            break

    if institution_name is None:
        raise InstitutionNotFoundError(f"Institution '{institution_id}' not found")

    # Create the Nordigen requisition
    reference = str(uuid.uuid4())
    try:
        provider = _build_provider()
        req = provider.create_requisition(
            institution_id=institution_id,
            redirect_uri=redirect_uri,
            reference=reference,
        )
    except ProviderError as exc:
        raise ConnectError(f"Failed to create requisition: {exc}") from exc

    requisition_id = req.get("id", "")
    link = req.get("link", "")

    # Persist a PENDING BankConnection
    conn = BankConnection(
        user_id=user_id,
        provider=BankProvider.NORDIGEN,
        institution_id=institution_id,
        institution_name=institution_name,
        external_reference=requisition_id,
        status=ConnectionStatus.PENDING,
    )
    db.add(conn)
    db.commit()
    db.refresh(conn)

    return {
        "id": conn.id,
        "requisition_id": requisition_id,
        "link": link,
        "status": ConnectionStatus.PENDING,
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
        # Already processed — return as-is
        return {
            "id": conn.id,
            "requisition_id": conn.external_reference,
            "status": conn.status,
            "institution_id": conn.institution_id,
            "institution_name": conn.institution_name,
            "accounts_created": [acc.id for acc in conn.accounts],
        }

    # Poll the provider
    try:
        provider = _build_provider()
        req = provider.get_requisition(conn.external_reference)
    except ProviderError as exc:
        raise ConnectError(f"Failed to poll requisition: {exc}") from exc

    nordigen_status = req.get("status", "")
    new_status = _normalise_status(nordigen_status)

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
    provider: NordigenAdapter,
) -> list[uuid.UUID]:
    """Fetch accounts from the provider and persist them."""
    created: list[uuid.UUID] = []
    try:
        provider_accounts = provider.fetch_accounts(conn.external_reference)
    except ProviderError:
        return created  # non-fatal — accounts will be fetched on next poll

    for pa in provider_accounts:
        # Check if already imported
        existing = db.scalar(
            select(Account).where(
                Account.external_account_id == pa.external_account_id,
                Account.user_id == conn.user_id,
            )
        )
        if existing is not None:
            continue

        # Map provider account type string to our enum
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

    # Deactivate all associated accounts
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
