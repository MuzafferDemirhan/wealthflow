from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import LogoutRequest, RefreshRequest, TokenPair
from app.schemas.user import UserCreate, UserRead
from app.services import auth_service

router = APIRouter()


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    """Register a new user account (FR-01)."""
    try:
        return auth_service.register_user(
            db,
            email=payload.email,
            password=payload.password,
            full_name=payload.full_name,
        )
    except auth_service.EmailAlreadyRegisteredError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )


@router.post("/login", response_model=TokenPair)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> TokenPair:
    """Login and receive a JWT access + refresh token pair (FR-02)."""
    try:
        access_token, refresh_token = auth_service.authenticate_user(
            db, email=form_data.username, password=form_data.password
        )
    except auth_service.InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenPair(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenPair)
async def refresh_token(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenPair:
    """Exchange a valid, unexpired refresh token for a new token pair (rotation)."""
    try:
        access_token, new_refresh_token = auth_service.refresh_access_token(
            db, raw_refresh_token=payload.refresh_token
        )
    except auth_service.InvalidRefreshTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenPair(access_token=access_token, refresh_token=new_refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(payload: LogoutRequest, db: Session = Depends(get_db)) -> None:
    """Revoke a refresh token. Idempotent — always succeeds."""
    auth_service.revoke_refresh_token(db, raw_refresh_token=payload.refresh_token)


@router.get("/me", response_model=UserRead)
async def read_current_user(current_user: User = Depends(get_current_active_user)) -> User:
    """Return the authenticated user's profile."""
    return current_user
