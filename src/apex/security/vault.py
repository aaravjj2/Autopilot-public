"""Encryption-at-rest for user-entered secrets (API keys, broker creds).

Uses Fernet (AES-128-CBC + HMAC-SHA256, authenticated) from the `cryptography`
library. The key comes from Settings.apex_secrets_key (a Fernet key). If that
is unset, a key is deterministically derived from apex_auth_secret so the app
still functions, but operators are warned to set an explicit APEX_SECRETS_KEY.

Plaintext secrets are NEVER logged, never returned by the API, and only
decrypted server-side at the moment of use.
"""

from __future__ import annotations

import base64
import hashlib
import logging
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

LOGGER = logging.getLogger(__name__)

_WARNED_DERIVED = False


def _derive_key(material: str) -> bytes:
    digest = hashlib.sha256(("apex-secrets-v1:" + material).encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def get_fernet(settings: Any | None = None) -> Fernet:
    global _WARNED_DERIVED
    if settings is None:
        from apex.core.config import get_settings

        settings = get_settings()
    key = (getattr(settings, "apex_secrets_key", "") or "").strip()
    if key:
        try:
            return Fernet(key.encode("utf-8") if isinstance(key, str) else key)
        except (ValueError, TypeError) as exc:
            LOGGER.warning("APEX_SECRETS_KEY invalid (%s); deriving from auth secret", exc)
    auth_secret = (getattr(settings, "apex_auth_secret", "") or "").strip() or "apex-dev-fallback"
    if not _WARNED_DERIVED:
        LOGGER.warning(
            "APEX_SECRETS_KEY not set; deriving encryption key from auth secret. "
            "Set an explicit APEX_SECRETS_KEY (Fernet.generate_key()) for production."
        )
        _WARNED_DERIVED = True
    return Fernet(_derive_key(auth_secret))


def encrypt_secret(plaintext: str, *, settings: Any | None = None) -> str:
    if not isinstance(plaintext, str) or not plaintext:
        raise ValueError("secret must be a non-empty string")
    token = get_fernet(settings).encrypt(plaintext.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_secret(ciphertext: str, *, settings: Any | None = None) -> str | None:
    """Return plaintext, or None if the token is invalid/tampered."""
    if not ciphertext:
        return None
    try:
        return get_fernet(settings).decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError, TypeError):
        return None


def mask_secret(plaintext: str) -> str:
    """Render a safe, non-reversible preview for UI/logs (last 4 only)."""
    if not plaintext:
        return ""
    if len(plaintext) <= 4:
        return "•" * len(plaintext)
    return "•" * (len(plaintext) - 4) + plaintext[-4:]
