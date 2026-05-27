"""Kalshi bounded scan and cached agent fallback."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from apex.domain.models import ArbOpportunity
from apex.integrations.kalshi_adapter import (
    KalshiEventClient,
    fetch_open_markets,
    market_volume_24h,
    normalize_orderbook,
)
from apex.services.pm_trading import load_cached_arb_opportunities


def test_market_volume_24h_reads_fp_fields():
    assert market_volume_24h({"volume_24h_fp": "12500.50"}) == 12500.50
    assert market_volume_24h({"volume_24h": 9000}) == 9000.0
    assert market_volume_24h({"liquidity_dollars": "42.5"}) == 42.5


def test_normalize_orderbook_fp():
    raw = {
        "orderbook_fp": {
            "yes_dollars": [["0.45", "10"]],
            "no_dollars": [["0.52", "8"]],
        }
    }
    ob = normalize_orderbook(raw)
    assert ob["yes"] == [[0.45, 10.0]]
    assert ob["no"] == [[0.52, 8.0]]


def test_fetch_open_markets_respects_max_markets(monkeypatch):
    pages = [
        {"markets": [{"ticker": f"T{i}", "volume_24h": 10000} for i in range(5)], "cursor": "c1"},
        {"markets": [{"ticker": f"T{i+5}", "volume_24h": 10000} for i in range(5)], "cursor": None},
    ]
    calls = {"n": 0}

    def fake_get(*_a, **_k):
        i = calls["n"]
        calls["n"] += 1
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json = MagicMock(return_value=pages[min(i, 1)])
        return resp

    monkeypatch.setattr("apex.integrations.kalshi_adapter.httpx.get", fake_get)
    out = fetch_open_markets(category="ECON", max_pages=1, max_markets=3)
    assert len(out) == 3


def test_get_macro_markets_bounded_orderbooks(monkeypatch, tmp_path):
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "audit.db"))
    from apex.core.config import get_settings

    get_settings.cache_clear()
    settings = get_settings()

    markets = [
        {"ticker": "KX-A", "title": "A", "volume_24h": 9000, "event_ticker": "E", "category": "ECON"},
        {"ticker": "KX-B", "title": "B", "volume_24h": 8000, "event_ticker": "E", "category": "ECON"},
    ]

    def fake_fetch(cat=None, **kwargs):
        return markets

    def fake_ob(ticker, **kwargs):
        return {"yes": [[0.45, 100]], "no": [[0.50, 100]]}

    monkeypatch.setattr(
        "apex.integrations.kalshi_adapter.fetch_open_markets", fake_fetch
    )
    monkeypatch.setattr(
        "apex.integrations.kalshi_adapter.fetch_orderbook", fake_ob
    )

    client = KalshiEventClient(settings)
    client.MACRO_CATEGORIES = ["ECON"]
    result = client.get_macro_markets(min_volume=1000, fast=True)
    assert len(result) == 2
    from apex.integrations.kalshi_adapter import get_last_kalshi_scan_metrics

    m = get_last_kalshi_scan_metrics()
    assert m.get("orderbooks_fetched", 0) >= 1


def test_load_cached_arb_opportunities(tmp_path, monkeypatch):
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "audit.db"))
    from apex.core.config import get_settings
    from apex.repositories.sqlite_store import SQLiteStore

    get_settings.cache_clear()
    settings = get_settings()
    store = SQLiteStore(settings.sqlite_path)
    opp = ArbOpportunity(
        id="cached-1",
        kalshi_ticker="KX-CACHE",
        poly_market_id="0xcache",
        question="Cached?",
        kalshi_title="Cached?",
        poly_title="Cached?",
        kalshi_yes_ask=0.4,
        poly_no_ask=0.5,
        gross_spread=0.1,
        net_edge=0.05,
        settlement_match_score=0.8,
        settlement_flags=[],
        volume_kalshi=10000,
        volume_poly=10000,
        category="macro",
        kelly_fraction=0.1,
    )
    store.save_arb_opportunities([opp])
    loaded = load_cached_arb_opportunities(store, settings)
    assert len(loaded) >= 1
    assert loaded[0].id == "cached-1"
