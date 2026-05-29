"""APEX security: authentication, authorization, secret vault, hardening.

Public surface kept small and explicit so callers (FastAPI app, tests) depend
on a stable contract.
"""

from __future__ import annotations

from apex.security.passwords import hash_password, verify_password
from apex.security.tokens import (
    TokenError,
    decode_token,
    make_access_token,
    make_guest_token,
    make_refresh_token,
)

__all__ = [
    "TokenError",
    "decode_token",
    "hash_password",
    "make_access_token",
    "make_guest_token",
    "make_refresh_token",
    "verify_password",
]
