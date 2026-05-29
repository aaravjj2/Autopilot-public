"""Unit tests for the security primitives: passwords, tokens, vault, ratelimit, store."""

from __future__ import annotations

import time
from types import SimpleNamespace

import pytest

from apex.security.passwords import (
    hash_password,
    validate_password_strength,
    verify_password,
)
from apex.security.ratelimit import SlidingWindowLimiter
from apex.security.store import AuthStore
from apex.security.tokens import (
    TokenError,
    decode_token,
    make_access_token,
    make_guest_token,
    make_refresh_token,
)
from apex.security.vault import decrypt_secret, encrypt_secret, mask_secret


def _settings(**kw):
    base = dict(
        apex_auth_secret="unit-test-secret-aaaaaaaaaaaaaaaaaaaa",
        apex_secrets_key="",
        access_token_ttl_min=30,
        refresh_token_ttl_days=14,
        guest_token_ttl_min=120,
    )
    base.update(kw)
    return SimpleNamespace(**base)


# -- passwords ---------------------------------------------------------------
def test_password_hash_roundtrip():
    h = hash_password("correct horse battery")
    assert h != "correct horse battery"
    assert verify_password("correct horse battery", h)
    assert not verify_password("wrong", h)


def test_password_rejects_weak():
    ok, _ = validate_password_strength("short")
    assert not ok
    with pytest.raises(ValueError):
        hash_password("password")


def test_password_long_inputs_not_collapsed():
    # bcrypt's 72-byte truncation must not make these equal (sha256 prehash).
    a = "A" * 100 + "1"
    b = "A" * 100 + "2"
    ha = hash_password(a)
    assert verify_password(a, ha)
    assert not verify_password(b, ha)


def test_verify_handles_garbage_without_raising():
    assert verify_password("x", "") is False
    assert verify_password("", "x") is False
    assert verify_password("x", "not-a-bcrypt-hash") is False


# -- tokens ------------------------------------------------------------------
def test_access_token_roundtrip():
    s = _settings()
    tok = make_access_token("user-1", "user", settings=s)
    claims = decode_token(tok, settings=s, expected_type="access")
    assert claims.sub == "user-1"
    assert claims.role == "user"
    assert claims.type == "access"


def test_guest_token_has_guest_role():
    s = _settings()
    claims = decode_token(make_guest_token(settings=s), settings=s)
    assert claims.role == "guest"
    assert claims.sub.startswith("guest:")


def test_token_type_mismatch_rejected():
    s = _settings()
    refresh, _ = make_refresh_token("u", "user", settings=s)
    with pytest.raises(TokenError):
        decode_token(refresh, settings=s, expected_type="access")


def test_forged_token_rejected():
    s = _settings()
    other = _settings(apex_auth_secret="a-totally-different-secret-bbbbbbbb")
    tok = make_access_token("u", "user", settings=other)
    with pytest.raises(TokenError):
        decode_token(tok, settings=s, expected_type="access")


def test_tampered_token_rejected():
    s = _settings()
    tok = make_access_token("u", "admin", settings=s)
    parts = tok.split(".")
    parts[1] = parts[1][:-2] + ("AA" if not parts[1].endswith("AA") else "BB")
    with pytest.raises(TokenError):
        decode_token(".".join(parts), settings=s)


def test_expired_token_rejected():
    s = _settings(access_token_ttl_min=5)
    # Build a token already expired by patching ttl via direct encode path.
    import apex.security.tokens as t

    tok = t._encode(
        sub="u", role="user", token_type="access", ttl_seconds=-3600, settings=s
    )
    with pytest.raises(TokenError):
        decode_token(tok, settings=s)


def test_none_algorithm_attack_rejected():
    s = _settings()
    import jwt

    payload = {
        "sub": "attacker",
        "role": "admin",
        "type": "access",
        "iss": "apex-autopilot",
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
    }
    forged = jwt.encode(payload, key="", algorithm="none")
    with pytest.raises(TokenError):
        decode_token(forged, settings=s)


# -- vault -------------------------------------------------------------------
def test_vault_encrypt_decrypt_roundtrip():
    s = _settings(apex_secrets_key="")
    cipher = encrypt_secret("sk-secret-value-123", settings=s)
    assert "sk-secret-value-123" not in cipher
    assert decrypt_secret(cipher, settings=s) == "sk-secret-value-123"


def test_vault_tampered_ciphertext_returns_none():
    s = _settings()
    cipher = encrypt_secret("topsecret", settings=s)
    assert decrypt_secret(cipher[:-3] + "AAA", settings=s) is None


def test_vault_wrong_key_cannot_decrypt():
    s1 = _settings(apex_auth_secret="key-one-aaaaaaaaaaaaaaaaaaaaaaaa")
    s2 = _settings(apex_auth_secret="key-two-bbbbbbbbbbbbbbbbbbbbbbbb")
    cipher = encrypt_secret("payload", settings=s1)
    assert decrypt_secret(cipher, settings=s2) is None


def test_mask_secret_hides_body():
    assert mask_secret("abcdefgh").endswith("efgh")
    assert mask_secret("abcdefgh").count("•") == 4
    assert mask_secret("ab") == "••"


# -- rate limiter ------------------------------------------------------------
def test_rate_limiter_blocks_after_max():
    lim = SlidingWindowLimiter(max_events=3, window_seconds=60)
    assert all(lim.allow("k") for _ in range(3))
    assert lim.allow("k") is False
    assert lim.allow("other") is True


# -- store -------------------------------------------------------------------
def test_store_user_crud(tmp_path):
    store = AuthStore(tmp_path / "auth.db")
    assert store.count_users() == 0
    u = store.create_user("Alice", hash_password("longpassword1"), role="admin")
    assert u["username"] == "alice"
    assert store.count_users() == 1
    with pytest.raises(ValueError):
        store.create_user("alice", "x")  # duplicate
    with pytest.raises(ValueError):
        store.create_user("ab", "x")  # too short
    assert store.get_user_by_username("ALICE")["id"] == u["id"]


def test_store_refresh_revocation(tmp_path):
    store = AuthStore(tmp_path / "auth.db")
    store.store_refresh("jti-1", "user-1", time.time() + 1000)
    assert store.is_refresh_valid("jti-1", "user-1")
    assert not store.is_refresh_valid("jti-1", "other-user")
    store.revoke_refresh("jti-1")
    assert not store.is_refresh_valid("jti-1", "user-1")


def test_store_expired_refresh_invalid(tmp_path):
    store = AuthStore(tmp_path / "auth.db")
    store.store_refresh("jti-old", "u", time.time() - 5)
    assert not store.is_refresh_valid("jti-old", "u")


def test_store_secret_vault(tmp_path):
    store = AuthStore(tmp_path / "auth.db")
    store.put_secret("u", "kalshi", "cipher-blob")
    assert store.list_secret_names("u") == ["kalshi"]
    assert store.get_secret_cipher("u", "kalshi") == "cipher-blob"
    assert store.delete_secret("u", "kalshi") is True
    assert store.list_secret_names("u") == []
