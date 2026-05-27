"""Kalshi demo Trade API client tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from apex.core.config import Settings
from apex.integrations.kalshi_trading import (
    KalshiTradingClient,
    kalshi_credentials_configured,
    kalshi_execution_venue,
)


def test_kalshi_credentials_configured_with_inline_key(tmp_path):
    settings = Settings(
        SQLITE_PATH=tmp_path / "audit.db",
        KALSHI_API_KEY="key-id",
        KALSHI_API_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\nMIIBogIBAAJBALtest\n-----END RSA PRIVATE KEY-----",
    )
    assert kalshi_credentials_configured(settings) is True


def test_kalshi_execution_venue_demo_flag(tmp_path):
    settings = Settings(
        SQLITE_PATH=tmp_path / "audit.db",
        KALSHI_DEMO_TRADING_ENABLED=True,
    )
    assert kalshi_execution_venue(settings) == "kalshi_demo"


@patch("apex.integrations.kalshi_trading.KalshiAuth")
@patch("apex.integrations.kalshi_trading.httpx.Client")
def test_create_yes_limit_buy(mock_client_cls, _mock_auth, tmp_path):
    settings = Settings(
        SQLITE_PATH=tmp_path / "audit.db",
        KALSHI_API_KEY="key-id",
        KALSHI_API_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\nMIIBogIBAAJBALtest\n-----END RSA PRIVATE KEY-----",
        KALSHI_BASE_URL="https://demo-api.kalshi.co/trade-api/v2",
    )
    mock_http = MagicMock()
    mock_client_cls.return_value = mock_http
    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_resp.content = b'{"order":{"order_id":"ord-abc","status":"resting"}}'
    mock_resp.json.return_value = {"order": {"order_id": "ord-abc", "status": "resting"}}
    mock_resp.text = mock_resp.content.decode()
    mock_http.request.return_value = mock_resp

    client = KalshiTradingClient(settings)
    result = client.create_yes_limit_buy("KX-TEST", stake_usd=50.0, price=0.5)

    assert result["order_id"] == "ord-abc"
    call_args = mock_http.request.call_args
    assert call_args[0][0] == "POST"
    assert call_args[0][1] == "/portfolio/orders"
    body = call_args[1]["json"]
    assert body["ticker"] == "KX-TEST"
    assert body["side"] == "yes"
    assert body["yes_price"] == 50
    assert body["count"] >= 1
