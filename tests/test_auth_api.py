"""End-to-end auth + authorization tests against the live FastAPI app.

Exercises the security middleware (fail-closed on mutating routes), guest mode,
register/login/refresh/logout, role gating on sensitive endpoints, the
encrypted key vault, and security headers.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import backend_api
from apex.security import store as auth_store_mod
from apex.security.store import AuthStore


@pytest.fixture()
def client(tmp_path, monkeypatch):
    # Isolate the auth DB per test and ensure auth is enforced.
    test_store = AuthStore(tmp_path / "auth_api.db")
    auth_store_mod.reset_auth_store_for_tests(test_store)
    monkeypatch.setattr(backend_api.settings, "auth_enabled", True, raising=False)
    monkeypatch.setattr(backend_api.settings, "cookie_secure", False, raising=False)
    monkeypatch.setattr(backend_api.settings, "auth_rate_limit_per_min", 1000, raising=False)
    monkeypatch.setattr(backend_api.settings, "api_rate_limit_per_min", 100000, raising=False)
    # Plain TestClient (no context manager) skips the heavy app lifespan startup.
    # raise_server_exceptions=False so downstream route errors surface as 500
    # responses (we assert on the auth gate, not the route's business logic).
    c = TestClient(backend_api.app, raise_server_exceptions=False)
    try:
        yield c
    finally:
        auth_store_mod.reset_auth_store_for_tests(None)


def test_reads_are_public(client):
    assert client.get("/health").status_code == 200


def test_mutating_endpoint_requires_auth(client):
    r = client.post("/api/arb/scan")
    assert r.status_code == 401
    assert r.headers.get("WWW-Authenticate") == "Bearer"


def test_security_headers_present(client):
    r = client.get("/health")
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"


def test_guest_can_access_general_mutating(client):
    g = client.post("/api/auth/guest")
    assert g.status_code == 200
    assert g.json()["role"] == "guest"
    # Cookie is now set on the client; a general mutating route should pass the gate.
    r = client.post("/api/arb/scan")
    assert r.status_code != 401  # gate passed (route may 200/4xx/5xx on its own logic)


def test_guest_blocked_from_sensitive(client):
    client.post("/api/auth/guest")
    r = client.post("/api/ml/train")
    assert r.status_code == 403


def test_register_first_user_is_admin_and_can_use_sensitive(client):
    r = client.post(
        "/api/auth/register",
        json={"username": "founder", "password": "strongpassword1"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["user"]["role"] == "admin"
    # Authenticated admin clears the sensitive gate (route logic may still vary).
    s = client.post("/api/ml/train")
    assert s.status_code != 401 and s.status_code != 403


def test_first_user_bootstraps_even_when_registration_disabled(client, monkeypatch):
    # Closed registration must still allow the very first (admin) account so a
    # fresh production deploy is never locked out, then block subsequent ones.
    monkeypatch.setattr(
        backend_api.settings, "allow_open_registration", False, raising=False
    )
    first = client.post(
        "/api/auth/register",
        json={"username": "rootadmin", "password": "strongpassword1"},
    )
    assert first.status_code == 200, first.text
    assert first.json()["user"]["role"] == "admin"
    client.post("/api/auth/logout")
    second = client.post(
        "/api/auth/register",
        json={"username": "intruder", "password": "strongpassword1"},
    )
    assert second.status_code == 403


def test_register_rejects_weak_password(client):
    r = client.post("/api/auth/register", json={"username": "weaky", "password": "123"})
    assert r.status_code == 400


def test_register_duplicate_username(client):
    client.post("/api/auth/register", json={"username": "dup", "password": "strongpassword1"})
    client.post("/api/auth/logout")
    r = client.post("/api/auth/register", json={"username": "dup", "password": "strongpassword1"})
    assert r.status_code == 400


def test_login_flow_and_me(client):
    client.post("/api/auth/register", json={"username": "lana", "password": "strongpassword1"})
    client.post("/api/auth/logout")
    bad = client.post("/api/auth/login", json={"username": "lana", "password": "nope"})
    assert bad.status_code == 401
    ok = client.post("/api/auth/login", json={"username": "lana", "password": "strongpassword1"})
    assert ok.status_code == 200
    me = client.get("/api/auth/me")
    assert me.json()["authenticated"] is True
    assert me.json()["username"] == "lana"


def test_refresh_rotates_and_old_token_revoked(client):
    reg = client.post(
        "/api/auth/register", json={"username": "rot", "password": "strongpassword1"}
    )
    old_refresh = reg.json()["refresh_token"]
    r1 = client.post("/api/auth/refresh")
    assert r1.status_code == 200
    # Drop the (rotated) cookie so the explicit old token is what gets validated.
    client.cookies.delete("apex_refresh")
    # Reusing the old (now revoked) refresh token must fail.
    r2 = client.post(
        "/api/auth/refresh", headers={"Authorization": f"Bearer {old_refresh}"}
    )
    assert r2.status_code == 401


def test_logout_clears_session(client):
    client.post("/api/auth/register", json={"username": "out", "password": "strongpassword1"})
    client.post("/api/auth/logout")
    me = client.get("/api/auth/me")
    assert me.json()["authenticated"] is False


def test_key_vault_requires_user_and_never_returns_plaintext(client):
    # Guest cannot manage keys.
    client.post("/api/auth/guest")
    assert client.get("/api/auth/keys").status_code in (401, 403)
    # Admin user can store/list/delete; plaintext is never echoed back.
    client.post("/api/auth/register", json={"username": "vault", "password": "strongpassword1"})
    put = client.put("/api/auth/keys/kalshi", json={"value": "super-secret-key-XYZ"})
    assert put.status_code == 200
    assert "super-secret-key-XYZ" not in put.text
    assert put.json()["preview"].endswith("XYZ")
    listing = client.get("/api/auth/keys")
    assert listing.json()["keys"] == ["kalshi"]
    assert "super-secret-key-XYZ" not in listing.text
    delete = client.delete("/api/auth/keys/kalshi")
    assert delete.status_code == 200
    assert client.get("/api/auth/keys").json()["keys"] == []


def test_one_user_cannot_read_another_users_keys(client):
    client.post("/api/auth/register", json={"username": "owner", "password": "strongpassword1"})
    client.put("/api/auth/keys/secret", json={"value": "owners-only"})
    client.post("/api/auth/logout")
    # Second user (not admin) registers; should see an empty vault.
    client.post("/api/auth/register", json={"username": "intruder", "password": "strongpassword1"})
    assert client.get("/api/auth/keys").json()["keys"] == []


def test_tampered_access_cookie_rejected(client):
    client.post("/api/auth/register", json={"username": "tamper", "password": "strongpassword1"})
    client.cookies.set("apex_access", "garbage.token.value")
    r = client.post("/api/arb/scan")
    assert r.status_code == 401


# ===========================================================================
# Red-team / fix-break loop: each attack below MUST be blocked.
# ===========================================================================
def test_redteam_sql_injection_in_login(client):
    client.post("/api/auth/register", json={"username": "victim", "password": "strongpassword1"})
    client.post("/api/auth/logout")
    for payload in (
        {"username": "victim' OR '1'='1", "password": "x"},
        {"username": "victim", "password": "' OR '1'='1' --"},
        {"username": "'; DROP TABLE users; --", "password": "whatever"},
    ):
        r = client.post("/api/auth/login", json=payload)
        assert r.status_code == 401, payload
    # Table intact: legitimate login still works.
    assert client.post(
        "/api/auth/login", json={"username": "victim", "password": "strongpassword1"}
    ).status_code == 200


def test_redteam_rs256_algorithm_confusion_rejected(client):
    import jwt
    from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    import time as _t

    forged = jwt.encode(
        {
            "sub": "attacker",
            "role": "admin",
            "type": "access",
            "iss": "apex-autopilot",
            "iat": int(_t.time()),
            "exp": int(_t.time()) + 3600,
        },
        key,
        algorithm="RS256",
    )
    client.cookies.set("apex_access", forged)
    assert client.post("/api/ml/train").status_code == 401


def test_redteam_access_token_cannot_be_used_as_refresh(client):
    reg = client.post(
        "/api/auth/register", json={"username": "confuse", "password": "strongpassword1"}
    )
    access = reg.json()["access_token"]
    client.cookies.delete("apex_refresh")
    r = client.post("/api/auth/refresh", headers={"Authorization": f"Bearer {access}"})
    assert r.status_code == 401


def test_redteam_login_rate_limited(client, monkeypatch):
    from apex.security import router as rtr

    rtr._login_limiter.reset()
    monkeypatch.setattr(backend_api.settings, "auth_rate_limit_per_min", 3, raising=False)
    codes = [
        client.post("/api/auth/login", json={"username": "nobody", "password": "bad"}).status_code
        for _ in range(6)
    ]
    assert 429 in codes
    rtr._login_limiter.reset()


def test_redteam_unauth_blocked_across_surfaces(client):
    for path in ("/api/agent/run/mission", "/orders", "/api/arb/scan", "/api/execute/sor"):
        r = client.post(path, json={})
        assert r.status_code in (401, 403), f"{path} -> {r.status_code}"


def test_redteam_key_name_path_traversal_is_isolated(client):
    client.post("/api/auth/register", json={"username": "trav", "password": "strongpassword1"})
    # A hostile key name is treated as an opaque DB key, never a filesystem path.
    put = client.put("/api/auth/keys/..%2f..%2fetc%2fpasswd", json={"value": "evil"})
    # 200 (stored as opaque key), 400 (rejected), or 404 (slashes don't route) are all safe.
    assert put.status_code in (200, 400, 404)
    # Also store a plainly-named hostile key to confirm DB-key opacity.
    client.put("/api/auth/keys/etc-passwd", json={"value": "evil"})
    # No plaintext leakage regardless.
    assert "evil" not in client.get("/api/auth/keys").text
