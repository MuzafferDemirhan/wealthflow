import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.connect import (
    AuthorizeRequest,
    ConnectionRead,
    InstitutionRead,
    RequisitionCreate,
    RequisitionCreateResponse,
    RequisitionRead,
)
from app.services import connect_service

router = APIRouter()


@router.get("/institutions", response_model=list[InstitutionRead])
async def list_institutions(
    country: str = Query("PL", min_length=2, max_length=2),
    current_user: User = Depends(get_current_active_user),
):
    """List supported banks/institutions available for linking."""
    try:
        return connect_service.list_institutions(country=country)
    except connect_service.ConnectError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        )


@router.post("/requisitions", response_model=RequisitionCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_requisition(
    payload: RequisitionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Initiate a bank link session — returns a redirect URL."""
    try:
        return connect_service.create_requisition(
            db,
            user_id=current_user.id,
            institution_id=payload.institution_id,
            redirect_uri=payload.redirect_uri,
        )
    except connect_service.InstitutionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Institution '{payload.institution_id}' not found",
        )
    except connect_service.ConnectError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        )


@router.post("/requisitions/{connection_id}/authorize", response_model=RequisitionRead)
async def authorize_requisition(
    connection_id: uuid.UUID,
    payload: AuthorizeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Exchange authorization code for a session after bank auth redirect."""
    try:
        return connect_service.authorize_requisition(
            db,
            connection_id=connection_id,
            user_id=current_user.id,
            code=payload.code,
        )
    except connect_service.RequisitionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Requisition not found",
        )
    except connect_service.ConnectError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        )


@router.get("/requisitions/{connection_id}", response_model=RequisitionRead)
async def get_requisition(
    connection_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Poll a requisition status and complete linking if bank reports LINKED."""
    try:
        return connect_service.poll_requisition(
            db,
            connection_id=connection_id,
            user_id=current_user.id,
        )
    except connect_service.RequisitionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Requisition not found",
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
