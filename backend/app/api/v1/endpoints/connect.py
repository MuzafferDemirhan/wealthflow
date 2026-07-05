import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.connect import (
    ConnectionRead,
    PlaidExchangeRequest,
    PlaidExchangeResponse,
    PlaidLinkTokenRequest,
    PlaidLinkTokenResponse,
)
from app.services import connect_service

router = APIRouter()


@router.post("/plaid/link-token", response_model=PlaidLinkTokenResponse)
async def create_plaid_link_token(
    payload: PlaidLinkTokenRequest,
    current_user: User = Depends(get_current_active_user),
):
    """
    Step 1: Create a Plaid link_token for the frontend Plaid Link SDK.
    The link_token is short-lived (30 min) and single-use.
    """
    try:
        return connect_service.create_plaid_link_token(
            user_id=current_user.id,
            redirect_uri=payload.redirect_uri,
        )
    except connect_service.ConnectError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        )


@router.post("/plaid/exchange", response_model=PlaidExchangeResponse, status_code=status.HTTP_201_CREATED)
async def exchange_plaid_token(
    payload: PlaidExchangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Step 2: Exchange the public_token received from Plaid Link for an access_token.
    The public_token is EPHEMERAL - it must be exchanged immediately.
    The access_token is stored encrypted; it is never returned to the client.
    """
    try:
        return connect_service.exchange_plaid_public_token(
            db,
            user_id=current_user.id,
            public_token=payload.public_token,
            institution_id=payload.institution_id,
            institution_name=payload.institution_name,
        )
    except connect_service.ConnectError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        )


@router.get("/connections", response_model=list[ConnectionRead])
async def list_connections(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List the user's bank connections."""
    return connect_service.get_user_connections(db, user_id=current_user.id)


@router.delete("/connections/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_connection(
    connection_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Revoke a bank connection and deactivate its accounts."""
    try:
        connect_service.disconnect_connection(
            db,
            connection_id=connection_id,
            user_id=current_user.id,
        )
    except connect_service.ConnectionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found",
        )
