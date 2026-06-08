"""Tests for apex.security.tokens — JWT issuance and validation."""
from __future__ import annotations

import time
from dataclasses import dataclass

import jwt
import pytest

from apex.security.tokens import (
    TokenClaims,
    TokenError,
    _secret,
    decode_token,
    make_access_token,
    make_guest_token,
    make_refresh_token,
)


@dataclass
class FakeSettings:
    """Minimal settings stub for testing."""
    apex_auth_secret: str = "test-secret-32chars-xxxxxxxxxxxxxxxx"
    access_token_ttl_min: int = 30
    refresh_token_ttl_days: int = 14
    guest_token_ttl_min: int = 120


# ---------------------------------------------------------------------------
# _secret
# ---------------------------------------------------------------------------

def test_secret_uses_configured_value():
    s = FakeSettings(apex_auth_secret="my-secret-key")
    assert _secret(s) == "my-secret-key"


def test_secret_falls_back_to_ephemeral_when_none():
    s = FakeSettings(apex_auth_secret="")
    result = _secret(s)
    assert isinstance(result, str)
    assert len(result) > 20


def test_secret_returns_ephemeral_for_none_settings():
    """_secret(None) should return an ephemeral key (string)."""
    result = _secret(None)
    assert isinstance(result, str)
    assert len(result) > 20


# ---------------------------------------------------------------------------
# make_access_token
# ---------------------------------------------------------------------------

def test_make_access_token_returns_jwt():
    s = FakeSettings()
    token = make_access_token("user:alice", "user", settings=s)
    assert isinstance(token, str)
    parts = token.split(".")
    assert len(parts) == 3  # header.payload.signature


def test_make_access_token_default_ttl():
    s = FakeSettings()
    token = make_access_token("user:bob", "admin", settings=s)
    claims = jwt.decode(token, s.apex_auth_secret, algorithms=["HS256"], issuer="apex-autopilot")
    assert claims["sub"] == "user:bob"
    assert claims["role"] == "admin"
    assert claims["type"] == "access"
    assert claims["iss"] == "apex-autopilot"


def test_make_access_token_no_settings():
    """Should still work with process-ephemeral secret."""
    token = make_access_token("guest:anon", "guest")
    assert isinstance(token, str)
    assert len(token.split(".")) == 3


# ---------------------------------------------------------------------------
# make_refresh_token
# ---------------------------------------------------------------------------

def test_make_refresh_token_returns_pair():
    s = FakeSettings()
    token, jti = make_refresh_token("user:carol", "user", settings=s)
    assert isinstance(token, str)
    assert isinstance(jti, str)
    assert len(jti) > 0


def test_make_refresh_token_has_correct_type():
    s = FakeSettings()
    token, _ = make_refresh_token("user:dave", "user", settings=s)
    claims = jwt.decode(token, s.apex_auth_secret, algorithms=["HS256"], issuer="apex-autopilot")
    assert claims["type"] == "refresh"


def test_make_refresh_token_with_custom_jti():
    s = FakeSettings()
    token, jti = make_refresh_token("user:eve", "admin", settings=s, jti="custom-jti-123")
    assert jti == "custom-jti-123"
    claims = jwt.decode(token, s.apex_auth_secret, algorithms=["HS256"], issuer="apex-autopilot")
    assert claims["jti"] == "custom-jti-123"


# ---------------------------------------------------------------------------
# make_guest_token
# ---------------------------------------------------------------------------

def test_make_guest_token_has_guest_role():
    s = FakeSettings()
    token = make_guest_token(settings=s)
    claims = jwt.decode(token, s.apex_auth_secret, algorithms=["HS256"], issuer="apex-autopilot")
    assert claims["role"] == "guest"
    assert claims["sub"].startswith("guest:")


def test_make_guest_token_no_settings():
    token = make_guest_token()
    assert isinstance(token, str)
    assert len(token.split(".")) == 3


# ---------------------------------------------------------------------------
# decode_token
# ---------------------------------------------------------------------------

def test_decode_token_valid_access(sample_settings: FakeSettings):
    token = make_access_token("user:frank", "user", settings=sample_settings)
    claims = decode_token(token, settings=sample_settings)
    assert isinstance(claims, TokenClaims)
    assert claims.sub == "user:frank"
    assert claims.role == "user"
    assert claims.type == "access"
    assert claims.jti
    assert claims.exp > time.time()


def test_decode_token_valid_expected_type(sample_settings: FakeSettings):
    token = make_access_token("user:grace", "user", settings=sample_settings)
    claims = decode_token(token, settings=sample_settings, expected_type="access")
    assert claims.type == "access"


def test_decode_token_wrong_type_raises(sample_settings: FakeSettings):
    token = make_access_token("user:heidi", "user", settings=sample_settings)
    with pytest.raises(TokenError, match="expected refresh token"):
        decode_token(token, settings=sample_settings, expected_type="refresh")


def test_decode_token_expired_raises():
    """Token with exp in the past should be rejected."""
    s = FakeSettings()
    from apex.security.tokens import _encode
    expired = _encode(
        sub="user:ivan",
        role="user",
        token_type="access",
        ttl_seconds=-60,  # expired 1 minute ago
        settings=s,
    )
    with pytest.raises(TokenError, match="token expired"):
        decode_token(expired, settings=s)


def test_decode_token_bad_signature_raises(sample_settings: FakeSettings):
    token = make_access_token("user:mallory", "user", settings=sample_settings)
    # Tamper with the signature portion
    parts = token.split(".")
    tampered = f"{parts[0]}.{parts[1]}.invalidsig"
    with pytest.raises(TokenError, match="invalid token"):
        decode_token(tampered, settings=sample_settings)


def test_decode_token_empty_raises():
    with pytest.raises(TokenError, match="missing token"):
        decode_token("")
    with pytest.raises(TokenError, match="missing token"):
        decode_token(None)  # type: ignore[arg-type]


def test_decode_token_bogus_string_raises():
    with pytest.raises(TokenError, match="invalid token"):
        decode_token("not.a.token")


def test_decode_token_invalid_role_raises():
    """Role must be one of guest/user/admin."""
    s = FakeSettings()
    from apex.security.tokens import _encode
    bad_role_token = _encode(
        sub="user:oscar",
        role="superadmin",  # not in allowed set
        token_type="access",
        ttl_seconds=300,
        settings=s,
    )
    with pytest.raises(TokenError, match="invalid role"):
        decode_token(bad_role_token, settings=s)


# ---------------------------------------------------------------------------
# decode_token without settings (uses ephemeral secret)
# ---------------------------------------------------------------------------

def test_decode_token_no_settings():
    token = make_access_token("guest:ephemeral", "guest")
    claims = decode_token(token)
    assert claims.sub == "guest:ephemeral"
    assert claims.role == "guest"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_settings() -> FakeSettings:
    return FakeSettings()
