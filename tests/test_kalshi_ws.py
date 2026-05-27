"""Unit tests for KalshiWsConnectionManager — no live connections required."""
from __future__ import annotations

import json
import time
from unittest.mock import patch

import pytest

from apex.integrations.kalshi_ws import KalshiWsConnectionManager


def _make_settings(tmp_path, demo=True):
    from apex.core.config import Settings

    base_url = (
        "https://demo-api.kalshi.co/trade-api/v2"
        if demo
        else "https://trading-api.kalshi.com/trade-api/v2"
    )
    return Settings(
        sqlite_path=tmp_path / "test.db",
        kalshi_base_url=base_url,
        demo_mode=demo,
        alpaca_paper_trade=True,
        kalshi_demo_trading_enabled=demo,
    )


def test_ws_url_demo(tmp_path):
    """Demo settings select the demo WebSocket endpoint."""
    settings = _make_settings(tmp_path, demo=True)
    mgr = KalshiWsConnectionManager(settings)
    assert "demo" in mgr._ws_url


def test_ws_url_prod(tmp_path):
    """Production settings select the production WebSocket endpoint."""
    from apex.core.config import Settings

    settings = Settings.model_construct(
        sqlite_path=tmp_path / "test.db",
        kalshi_base_url="https://trading-api.kalshi.com/trade-api/v2",
        demo_mode=False,
        alpaca_paper_trade=True,
        kalshi_demo_trading_enabled=False,
        redis_url="redis://127.0.0.1:6379/0",
    )
    mgr = KalshiWsConnectionManager(settings)
    assert "demo" not in mgr._ws_url


def test_subscribe_msg_structure(tmp_path):
    """Subscribe payload includes orderbook_delta channel and tickers."""
    settings = _make_settings(tmp_path)
    mgr = KalshiWsConnectionManager(settings)
    msg = json.loads(mgr._subscribe_msg(["KX-FED-25", "KX-CPI-25"]))
    assert msg["cmd"] == "subscribe"
    assert "orderbook_delta" in msg["params"]["channels"]
    assert "KX-FED-25" in msg["params"]["market_tickers"]


def test_parse_frame_snapshot(tmp_path):
    """Snapshot frames expose ticker and type."""
    settings = _make_settings(tmp_path)
    mgr = KalshiWsConnectionManager(settings)
    raw = json.dumps(
        {
            "type": "orderbook_snapshot",
            "params": {"market_ticker": "KX-FED-25"},
            "result": {"yes": [[0.48, 100]], "no": [[0.52, 100]]},
        }
    )
    msg_type, ticker, payload = mgr._parse_frame(raw)
    assert msg_type == "orderbook_snapshot"
    assert ticker == "KX-FED-25"
    assert payload is not None


def test_parse_frame_delta(tmp_path):
    """Delta frames expose ticker and type."""
    settings = _make_settings(tmp_path)
    mgr = KalshiWsConnectionManager(settings)
    raw = json.dumps(
        {
            "type": "orderbook_delta",
            "params": {"market_ticker": "KX-FED-25"},
            "result": {"side": "yes", "price": 0.49, "quantity": 200},
        }
    )
    msg_type, ticker, payload = mgr._parse_frame(raw)
    assert msg_type == "orderbook_delta"
    assert ticker == "KX-FED-25"


def test_parse_frame_invalid_json(tmp_path):
    """Invalid JSON returns empty parse tuple."""
    settings = _make_settings(tmp_path)
    mgr = KalshiWsConnectionManager(settings)
    msg_type, ticker, payload = mgr._parse_frame("not json {{{")
    assert msg_type is None
    assert ticker is None


def test_apply_frame_snapshot_calls_ingest(tmp_path):
    """Snapshot frames write to Redis via ingest_orderbook."""
    settings = _make_settings(tmp_path)
    mgr = KalshiWsConnectionManager(settings)
    payload = {
        "type": "orderbook_snapshot",
        "result": {"yes": [[0.48, 100]], "no": [[0.52, 200]]},
    }
    with patch("apex.cache.orderbook_l2.ingest_orderbook") as mock_ingest:
        mgr._apply_frame("orderbook_snapshot", "KX-TEST", payload)
        mock_ingest.assert_called_once()
        call_args = mock_ingest.call_args
        assert call_args[0][0] == "KALSHI"
        assert call_args[0][1] == "KX-TEST"


def test_stale_detection(tmp_path):
    """Stale when no messages; fresh after a frame is applied."""
    settings = _make_settings(tmp_path)
    mgr = KalshiWsConnectionManager(settings)
    assert mgr.is_stale is True
    mgr._last_message_at = time.monotonic()
    assert mgr.is_stale is False


def test_stale_startup_grace(tmp_path):
    """Recently connected socket should not be marked stale immediately."""
    settings = _make_settings(tmp_path)
    mgr = KalshiWsConnectionManager(settings)
    mgr._connected_at = time.monotonic()
    assert mgr.is_stale is False


def test_stale_uses_last_frame_when_no_book_updates(tmp_path):
    """Heartbeat-only frames keep connection fresh."""
    settings = _make_settings(tmp_path)
    mgr = KalshiWsConnectionManager(settings)
    mgr._connected_at = time.monotonic() - 600
    mgr._last_frame_at = time.monotonic()
    assert mgr.is_stale is False


def test_stop_sets_running_false(tmp_path):
    """stop() clears the run loop flag."""
    settings = _make_settings(tmp_path)
    mgr = KalshiWsConnectionManager(settings)
    mgr._running = True
    mgr.stop()
    assert mgr._running is False
