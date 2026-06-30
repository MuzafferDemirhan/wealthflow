"""
Password hashing and JWT token utilities.

Access tokens and refresh tokens are both JWTs but serve different
purposes, distinguished by a `type` claim ("access" / "refresh") so
that one cannot be replayed as the other even if `SECRET_KEY` and
algorithm match.
"""

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

ALGORITHM = "HS256"

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"


def hash_password(plain_password: str) -> str:
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return _pwd_context.verify(plain_password, hashed_password)


def _create_token(
    subject: str,
    token_type: TokenType,
    expires_delta: timedelta,
    extra_claims: dict[str, Any] | None = None,
) -> tuple[str, str, datetime]:
    """Returns (encoded_jwt, jti, expires_at)."""
    now = datetime.now(timezone.utc)
    expire = now + expires_delta
    jti = str(uuid.uuid4())

    to_encode: dict[str, Any] = {
        "sub": subject,
        "type": token_type.value,
        "iat": now,
        "exp": expire,
        "jti": jti,
    }
    if extra_claims:
        to_encode.update(extra_claims)

    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt, jti, expire


def create_access_token(user_id: uuid.UUID, role: str) -> str:
    token, _, _ = _create_token(
        subject=str(user_id),
        token_type=TokenType.ACCESS,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        extra_claims={"role": role},
    )
    return token


def create_refresh_token(user_id: uuid.UUID) -> tuple[str, str, datetime]:
    """Returns (token, jti, expires_at) — caller persists the hash + expiry."""
    return _create_token(
        subject=str(user_id),
        token_type=TokenType.REFRESH,
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str) -> dict[str, Any] | None:
    """Decode and validate a JWT's signature and expiry. Returns claims or None."""
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


def hash_token(raw_token: str) -> str:
    """
    SHA-256 digest used to store/look up refresh tokens at rest.

    Refresh tokens are JWTs (often >72 bytes), so bcrypt — which
    silently truncates input — is not appropriate here. SHA-256 is
    fine for this purpose because the token itself already carries
    high entropy (it isn't a low-entropy user-chosen secret).
    """
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
