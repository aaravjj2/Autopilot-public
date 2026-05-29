"""Password hashing with bcrypt.

bcrypt silently truncates inputs at 72 bytes, which can weaken long passwords
and create surprising equality of distinct passwords. We pre-hash with
SHA-256 (base64) so the full password entropy is preserved before bcrypt, a
well-established pattern. Hashes are salted per-password by bcrypt.
"""

from __future__ import annotations

import base64
import hashlib

import bcrypt

_BCRYPT_ROUNDS = 12
_MIN_LEN = 8
_MAX_LEN = 256


def _prehash(password: str) -> bytes:
    digest = hashlib.sha256(password.encode("utf-8")).digest()
    return base64.b64encode(digest)


def validate_password_strength(password: str) -> tuple[bool, str | None]:
    """Lightweight policy: length + not trivially weak. Returns (ok, reason)."""
    if not isinstance(password, str):
        return False, "password must be a string"
    if len(password) < _MIN_LEN:
        return False, f"password must be at least {_MIN_LEN} characters"
    if len(password) > _MAX_LEN:
        return False, f"password must be at most {_MAX_LEN} characters"
    lowered = password.lower()
    if lowered in {"password", "12345678", "qwertyui", "letmein1", "changeme"}:
        return False, "password is too common"
    return True, None


def hash_password(password: str) -> str:
    ok, reason = validate_password_strength(password)
    if not ok:
        raise ValueError(reason)
    return bcrypt.hashpw(_prehash(password), bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Constant-time verify. Never raises on malformed input (returns False)."""
    if not password or not hashed:
        return False
    try:
        return bcrypt.checkpw(_prehash(password), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False
