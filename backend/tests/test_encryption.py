"""
Tests for token encryption/decryption.

These tests do NOT need a database - they test the encrypt/decrypt
logic in isolation using a known Fernet key.
"""

import re

import pytest
from cryptography.fernet import Fernet

from app.core.encryption import _get_fernet, decrypt_token, encrypt_token


@pytest.fixture(autouse=True)
def set_encryption_key(monkeypatch):
    """Set a valid Fernet key for the duration of each test."""
    key = Fernet.generate_key().decode()
    monkeypatch.setattr("app.core.config.settings.TOKEN_ENCRYPTION_KEY", key)


def test_encrypt_decrypt_roundtrip():
    plaintext = "plaid_access_token_abc123"
    ciphertext = encrypt_token(plaintext)
    assert ciphertext != plaintext
    assert re.match(r"^[A-Za-z0-9\-_=]+$", ciphertext)
    decrypted = decrypt_token(ciphertext)
    assert decrypted == plaintext


def test_encrypt_produces_different_ciphertexts():
    """Same plaintext should produce different ciphertext each time (IV/nonce)."""
    p = "same_value"
    c1 = encrypt_token(p)
    c2 = encrypt_token(p)
    assert c1 != c2
    assert decrypt_token(c1) == p
    assert decrypt_token(c2) == p


def test_decrypt_tampered_data_raises_value_error():
    ciphertext = encrypt_token("secret")
    # Tamper with the ciphertext
    tampered = ciphertext[:-5] + "ZZZZZ"
    with pytest.raises(ValueError, match="Token decryption failed"):
        decrypt_token(tampered)


def test_decrypt_wrong_key_raises_value_error(monkeypatch):
    ciphertext = encrypt_token("secret")
    # Change the key
    other_key = Fernet.generate_key().decode()
    monkeypatch.setattr("app.core.config.settings.TOKEN_ENCRYPTION_KEY", other_key)
    with pytest.raises(ValueError, match="Token decryption failed"):
        decrypt_token(ciphertext)


def test_missing_key_raises_runtime_error(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.TOKEN_ENCRYPTION_KEY", "")
    with pytest.raises(RuntimeError, match="TOKEN_ENCRYPTION_KEY is not set"):
        _get_fernet()
