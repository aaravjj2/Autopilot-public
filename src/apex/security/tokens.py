"""JWT issuance/validation for access, refresh, and guest tokens.

Uses HS256 with a server secret (Settings.apex_auth_secret). If no secret is
configured, a process-ephemeral secret is generated and a warning logged, so
the app stays functional in dev/test while still rejecting cross-restart and
forged tokens. In production the secret MUST come from the environment /
Secret Manager.
"""

from __future__ import annotations

import logging
import secrets
import time
import uuid
from dataclasses import dataclass
from typing import Any

import jwt

LOGGER = logging.getLogger(__name__)

_ALGO = "HS256"
_ISSUER = "apex-autopilot"
_LEEWAY_SEC = 10

# Process-ephemeral fallback secret (only used when none configured).
_EPHEMERAL_SECRET = secrets.token_urlsafe(48)
_WARNED_EPHEMERAL = False


class TokenError(Exception):
    """Raised when a token is missing, malformed, expired, or forged."""


@dataclass
class TokenClaims:
    sub: str
    role: str
    type: str
    jti: str
    exp: int
    raw: dict[str, Any]


def _secret(settings: Any | None) -> str:
    global _WARNED_EPHEMERAL
    if settings is None:
        try:
            from apex.core.config import get_settings

            settings = get_settings()
        except Exception:
            settings = None
    configured = (getattr(settings, "apex_auth_secret", "") or "").strip() if settings else ""
    if configured:
        return configured
    if not _WARNED_EPHEMERAL:
        LOGGER.warning(
            "APEX_AUTH_SECRET not set; using a process-ephemeral JWT secret. "
            "Tokens will not survive restarts. Set APEX_AUTH_SECRET in env/Secret Manager."
        )
        _WARNED_EPHEMERAL = True
    return _EPHEMERAL_SECRET


def _encode(
    *,
    sub: str,
    role: str,
    token_type: str,
    ttl_seconds: int,
    settings: Any | None,
    jti: str | None = None,
) -> str:
    now = int(time.time())
    payload = {
        "sub": sub,
        "role": role,
        "type": token_type,
        "jti": jti or uuid.uuid4().hex,
        "iat": now,
        "nbf": now,
        "exp": now + int(ttl_seconds),
        "iss": _ISSUER,
    }
    return jwt.encode(payload, _secret(settings), algorithm=_ALGO)


def make_access_token(sub: str, role: str, *, settings: Any | None = None) -> str:
    ttl_min = int(getattr(settings, "access_token_ttl_min", 30) or 30) if settings else 30
    return _encode(
        sub=sub, role=role, token_type="access", ttl_seconds=ttl_min * 60, settings=settings
    )


def make_refresh_token(
    sub: str, role: str, *, settings: Any | None = None, jti: str | None = None
) -> tuple[str, str]:
    """Return (token, jti). jti is tracked server-side for revocation."""
    ttl_days = int(getattr(settings, "refresh_token_ttl_days", 14) or 14) if settings else 14
    jti = jti or uuid.uuid4().hex
    token = _encode(
        sub=sub,
        role=role,
        token_type="refresh",
        ttl_seconds=ttl_days * 86400,
        settings=settings,
        jti=jti,
    )
    return token, jti


def make_guest_token(*, settings: Any | None = None) -> str:
    ttl_min = int(getattr(settings, "guest_token_ttl_min", 120) or 120) if settings else 120
    return _encode(
        sub=f"guest:{uuid.uuid4().hex[:12]}",
        role="guest",
        token_type="access",
        ttl_seconds=ttl_min * 60,
        settings=settings,
    )


def decode_token(token: str, *, settings: Any | None = None, expected_type: str | None = None) -> TokenClaims:
    if not token or not isinstance(token, str):
        raise TokenError("missing token")
    try:
        payload = jwt.decode(
            token,
            _secret(settings),
            algorithms=[_ALGO],
            issuer=_ISSUER,
            leeway=_LEEWAY_SEC,
            options={"require": ["exp", "iat", "sub", "iss"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError(f"invalid token: {exc}") from exc
    token_type = str(payload.get("type", ""))
    if expected_type and token_type != expected_type:
        raise TokenError(f"expected {expected_type} token, got {token_type or 'unknown'}")
    role = str(payload.get("role", ""))
    if role not in {"guest", "user", "admin"}:
        raise TokenError("invalid role")
    return TokenClaims(
        sub=str(payload["sub"]),
        role=role,
        type=token_type,
        jti=str(payload.get("jti", "")),
        exp=int(payload["exp"]),
        raw=payload,
    )
