"""FastAPI auth dependencies + principal extraction.

Tokens are read from httpOnly cookies first (browser flow) and fall back to an
``Authorization: Bearer`` header (programmatic flow). Reads stay public; the
``auth_required`` factory gates mutating/sensitive endpoints by minimum role.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from fastapi import HTTPException, Request

from apex.core.config import get_settings
from apex.security.tokens import TokenClaims, TokenError, decode_token

ACCESS_COOKIE = "apex_access"
REFRESH_COOKIE = "apex_refresh"

_ROLE_RANK = {"guest": 0, "user": 1, "admin": 2}


@dataclass
class Principal:
    sub: str
    role: str
    is_guest: bool
    authenticated: bool

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


class AuthError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _extract_token(request: Request) -> str | None:
    token = request.cookies.get(ACCESS_COOKIE)
    if token:
        return token
    header = request.headers.get("authorization") or request.headers.get("Authorization")
    if header and header.lower().startswith("bearer "):
        return header[7:].strip() or None
    return None


def current_principal(request: Request, *, settings: Any | None = None) -> Principal | None:
    """Best-effort principal; returns None when no valid token is present."""
    settings = settings or get_settings()
    token = _extract_token(request)
    if not token:
        return None
    try:
        claims: TokenClaims = decode_token(token, settings=settings, expected_type="access")
    except TokenError:
        return None
    return Principal(
        sub=claims.sub,
        role=claims.role,
        is_guest=claims.role == "guest",
        authenticated=claims.role != "guest",
    )


def auth_required(min_role: str = "guest") -> Callable[[Request], Principal]:
    """Build a dependency enforcing a minimum role.

    When auth is disabled (local dev), returns a synthetic admin principal so the
    app stays fully usable without login.
    """
    floor = _ROLE_RANK.get(min_role, 0)

    def _dep(request: Request) -> Principal:
        settings = get_settings()
        if not settings.auth_enabled:
            return Principal(sub="local-dev", role="admin", is_guest=False, authenticated=True)
        principal = current_principal(request, settings=settings)
        if principal is None:
            raise HTTPException(
                status_code=401,
                detail="authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if _ROLE_RANK.get(principal.role, 0) < floor:
            raise HTTPException(status_code=403, detail="insufficient privileges")
        return principal

    return _dep
