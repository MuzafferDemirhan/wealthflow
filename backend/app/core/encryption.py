"""
Symmetric encryption for sensitive values stored in the DB (e.g. Plaid access_token).
Uses Fernet (AES-128-CBC + HMAC-SHA256). Keys must be stored in environment variables.
"""

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def _get_fernet() -> Fernet:
    key = settings.TOKEN_ENCRYPTION_KEY
    if not key:
        raise RuntimeError(
            "TOKEN_ENCRYPTION_KEY is not set. "
            "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    return Fernet(key.encode())


def encrypt_token(plaintext: str) -> str:
    """Encrypt a sensitive string. Returns a URL-safe base64 ciphertext string."""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_token(ciphertext: str) -> str:
    """Decrypt a previously encrypted string. Raises ValueError on tamper/wrong key."""
    try:
        return _get_fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise ValueError(
            "Token decryption failed — possible key mismatch or data corruption"
        ) from exc
