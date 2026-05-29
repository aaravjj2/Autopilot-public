"""Auth + secret-vault HTTP routes.

Browser flow uses httpOnly cookies; programmatic clients may use the returned
bearer tokens. Login/register are rate limited per client IP. Secrets are
encrypted at rest and never returned in plaintext.
"""

from __future__ import annotations

import time

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response

from apex.core.config import get_settings
from apex.security.deps import (
    ACCESS_COOKIE,
    REFRESH_COOKIE,
    Principal,
    auth_required,
    current_principal,
)
from apex.security.passwords import hash_password, validate_password_strength, verify_password
from apex.security.ratelimit import SlidingWindowLimiter
from apex.security.store import get_auth_store
from apex.security.tokens import (
    TokenError,
    decode_token,
    make_access_token,
    make_guest_token,
    make_refresh_token,
)
from apex.security.vault import decrypt_secret, encrypt_secret, mask_secret

router = APIRouter(prefix="/api/auth", tags=["auth"])

_login_limiter = SlidingWindowLimiter(max_events=10, window_seconds=60.0)


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _rate_limit(request: Request, scope: str) -> None:
    settings = get_settings()
    _login_limiter.max_events = int(settings.auth_rate_limit_per_min)
    key = f"{scope}:{_client_ip(request)}"
    if not _login_limiter.allow(key):
        retry = int(_login_limiter.retry_after(key)) + 1
        raise HTTPException(
            status_code=429,
            detail="too many attempts; slow down",
            headers={"Retry-After": str(retry)},
        )


def _set_auth_cookies(response: Response, access: str, refresh: str | None) -> None:
    settings = get_settings()
    secure = bool(settings.cookie_secure)
    samesite = (settings.cookie_samesite or "lax").lower()
    if samesite not in {"lax", "strict", "none"}:
        samesite = "lax"
    response.set_cookie(
        ACCESS_COOKIE,
        access,
        httponly=True,
        secure=secure,
        samesite=samesite,
        max_age=int(settings.access_token_ttl_min) * 60,
        path="/",
    )
    if refresh is not None:
        response.set_cookie(
            REFRESH_COOKIE,
            refresh,
            httponly=True,
            secure=secure,
            samesite=samesite,
            max_age=int(settings.refresh_token_ttl_days) * 86400,
            path="/api/auth",
        )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(REFRESH_COOKIE, path="/api/auth")


def _issue_session(response: Response, user_id: str, role: str) -> dict:
    settings = get_settings()
    store = get_auth_store(settings)
    access = make_access_token(user_id, role, settings=settings)
    refresh, jti = make_refresh_token(user_id, role, settings=settings)
    expires = time.time() + int(settings.refresh_token_ttl_days) * 86400
    store.store_refresh(jti, user_id, expires)
    _set_auth_cookies(response, access, refresh)
    return {"access_token": access, "refresh_token": refresh, "token_type": "bearer"}


@router.post("/register")
def register(request: Request, response: Response, payload: dict = Body(...)) -> dict:
    settings = get_settings()
    _rate_limit(request, "register")
    store = get_auth_store(settings)
    existing = store.count_users()
    # Bootstrap: the very first account (the admin) can always be created so a
    # freshly deployed instance is not locked out. After that, honor the flag.
    if existing > 0 and not settings.allow_open_registration:
        raise HTTPException(status_code=403, detail="registration is disabled")
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))
    ok, reason = validate_password_strength(password)
    if not ok:
        raise HTTPException(status_code=400, detail=reason or "weak password")
    # First registered user becomes admin; subsequent users are standard.
    role = "admin" if existing == 0 else "user"
    try:
        user = store.create_user(username, hash_password(password), role=role)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    tokens = _issue_session(response, user["id"], user["role"])
    return {"user": {"id": user["id"], "username": user["username"], "role": user["role"]}, **tokens}


@router.post("/login")
def login(request: Request, response: Response, payload: dict = Body(...)) -> dict:
    _rate_limit(request, "login")
    settings = get_settings()
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))
    store = get_auth_store(settings)
    user = store.get_user_by_username(username)
    # Always run a verify to keep timing uniform whether or not the user exists.
    placeholder = "$2b$12$" + "a" * 53
    ok = verify_password(password, user["password_hash"] if user else placeholder)
    if not user or not ok or int(user.get("disabled", 0)) == 1:
        raise HTTPException(status_code=401, detail="invalid credentials")
    tokens = _issue_session(response, user["id"], user["role"])
    return {"user": {"id": user["id"], "username": user["username"], "role": user["role"]}, **tokens}


@router.post("/guest")
def guest(response: Response) -> dict:
    settings = get_settings()
    token = make_guest_token(settings=settings)
    _set_auth_cookies(response, token, None)
    return {"access_token": token, "token_type": "bearer", "role": "guest"}


@router.post("/refresh")
def refresh(request: Request, response: Response) -> dict:
    settings = get_settings()
    token = request.cookies.get(REFRESH_COOKIE)
    if not token:
        header = request.headers.get("authorization", "")
        if header.lower().startswith("bearer "):
            token = header[7:].strip()
    if not token:
        raise HTTPException(status_code=401, detail="missing refresh token")
    try:
        claims = decode_token(token, settings=settings, expected_type="refresh")
    except TokenError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    store = get_auth_store(settings)
    if not store.is_refresh_valid(claims.jti, claims.sub):
        raise HTTPException(status_code=401, detail="refresh token revoked or expired")
    # Rotate: revoke the used refresh token, issue a fresh pair.
    store.revoke_refresh(claims.jti)
    user = store.get_user_by_id(claims.sub)
    role = user["role"] if user else claims.role
    tokens = _issue_session(response, claims.sub, role)
    return {"rotated": True, **tokens}


@router.post("/logout")
def logout(request: Request, response: Response) -> dict:
    settings = get_settings()
    token = request.cookies.get(REFRESH_COOKIE)
    if token:
        try:
            claims = decode_token(token, settings=settings, expected_type="refresh")
            get_auth_store(settings).revoke_refresh(claims.jti)
        except TokenError:
            pass
    _clear_auth_cookies(response)
    return {"ok": True}


@router.get("/me")
def me(request: Request) -> dict:
    principal = current_principal(request)
    if principal is None:
        return {"authenticated": False, "role": None}
    out: dict = {
        "authenticated": principal.authenticated,
        "role": principal.role,
        "is_guest": principal.is_guest,
        "sub": principal.sub,
    }
    if principal.authenticated:
        user = get_auth_store().get_user_by_id(principal.sub)
        if user:
            out["username"] = user["username"]
    return out


# -- secret vault (user/admin only) -----------------------------------------
@router.get("/keys")
def list_keys(principal: Principal = Depends(auth_required("user"))) -> dict:
    names = get_auth_store().list_secret_names(principal.sub)
    return {"keys": names}


@router.put("/keys/{name}")
def put_key(
    name: str,
    payload: dict = Body(...),
    principal: Principal = Depends(auth_required("user")),
) -> dict:
    value = str(payload.get("value", ""))
    if not value:
        raise HTTPException(status_code=400, detail="value is required")
    if len(value) > 8192:
        raise HTTPException(status_code=400, detail="value too large")
    try:
        cipher = encrypt_secret(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        get_auth_store().put_secret(principal.sub, name, cipher)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "name": name.strip(), "preview": mask_secret(value)}


@router.delete("/keys/{name}")
def delete_key(name: str, principal: Principal = Depends(auth_required("user"))) -> dict:
    deleted = get_auth_store().delete_secret(principal.sub, name)
    if not deleted:
        raise HTTPException(status_code=404, detail="key not found")
    return {"ok": True, "deleted": name.strip()}


def get_user_secret(user_id: str, name: str) -> str | None:
    """Server-side accessor: decrypt a stored secret for use (never exposed)."""
    cipher = get_auth_store().get_secret_cipher(user_id, name)
    if not cipher:
        return None
    return decrypt_secret(cipher)
