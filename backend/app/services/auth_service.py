"""
Authentication business logic, kept out of the endpoint layer so it
can be unit tested without spinning up FastAPI/HTTP.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User


class AuthError(Exception):
    """Base class for expected auth failures the endpoint layer maps to HTTP errors."""


class EmailAlreadyRegisteredError(AuthError):
    pass


class InvalidCredentialsError(AuthError):
    pass


class InvalidRefreshTokenError(AuthError):
    pass


def register_user(db: Session, *, email: str, password: str, full_name: str) -> User:
    existing = db.scalar(select(User).where(User.email == email))
    if existing is not None:
        raise EmailAlreadyRegisteredError(email)

    user = User(
        email=email,
        hashed_password=hash_password(password),
        full_name=full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _issue_token_pair(db: Session, user: User) -> tuple[str, str]:
    access_token = create_access_token(user_id=user.id, role=user.role.value)
    refresh_token, jti, expires_at = create_refresh_token(user_id=user.id)

    db.add(
        RefreshToken(
            id=uuid.UUID(jti),
            user_id=user.id,
            token_hash=hash_token(refresh_token),
            expires_at=expires_at,
        )
    )
    db.commit()
    return access_token, refresh_token


def authenticate_user(db: Session, *, email: str, password: str) -> tuple[str, str]:
    """Verify credentials and return (access_token, refresh_token)."""
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(password, user.hashed_password):
        raise InvalidCredentialsError()
    if not user.is_active:
        raise InvalidCredentialsError()

    return _issue_token_pair(db, user)


def refresh_access_token(db: Session, *, raw_refresh_token: str) -> tuple[str, str]:
    """
    Validate + rotate a refresh token.

    Returns a brand new (access_token, refresh_token) pair. The
    presented refresh token is revoked as part of rotation, so it
    cannot be replayed even if it leaks afterwards.
    """
    claims = decode_token(raw_refresh_token)
    if claims is None or claims.get("type") != "refresh":
        raise InvalidRefreshTokenError()

    token_hash = hash_token(raw_refresh_token)
    stored = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    if stored is None or stored.revoked:
        raise InvalidRefreshTokenError()

    stored_expires_at = stored.expires_at
    if stored_expires_at.tzinfo is None:
        stored_expires_at = stored_expires_at.replace(tzinfo=timezone.utc)

    if stored_expires_at < datetime.now(timezone.utc):
        raise InvalidRefreshTokenError()

    user = db.get(User, stored.user_id)
    if user is None or not user.is_active:
        raise InvalidRefreshTokenError()

    stored.revoked = True
    db.add(stored)

    return _issue_token_pair(db, user)


def revoke_refresh_token(db: Session, *, raw_refresh_token: str) -> None:
    """Idempotent logout — unknown/already-revoked tokens are silently accepted."""
    token_hash = hash_token(raw_refresh_token)
    stored = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    if stored is not None and not stored.revoked:
        stored.revoked = True
        db.add(stored)
        db.commit()
