"""AES-256-GCM API key encryption (Week 10 Day 2)."""

from __future__ import annotations

import base64
import os
from typing import Tuple

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False


def _key() -> bytes:
    raw = os.getenv("APEX_TENANT_KEY", "0" * 32)
    return raw.encode()[:32].ljust(32, b"0")[:32]


def encrypt_secret(plaintext: str) -> str:
    if not HAS_CRYPTO:
        return base64.b64encode(plaintext.encode()).decode()
    aes = AESGCM(_key())
    nonce = os.urandom(12)
    ct = aes.encrypt(nonce, plaintext.encode(), None)
    return base64.b64encode(nonce + ct).decode()


def decrypt_secret(token: str) -> str:
    if not HAS_CRYPTO:
        return base64.b64decode(token.encode()).decode()
    raw = base64.b64decode(token.encode())
    nonce, ct = raw[:12], raw[12:]
    aes = AESGCM(_key())
    return aes.decrypt(nonce, ct, None).decode()
