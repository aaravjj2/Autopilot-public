"""M07 should use Redis L2 cache when available, skip live HTTP."""
from __future__ import annotations

import threading
from unittest.mock import MagicMock


from apex.core.config import Settings
from apex.domain.models import ArbOpportunity


def _make_opp(**kwargs) -> ArbOpportunity:
    defaults = dict(
        kalshi_ticker="KX-TEST",
        poly_market_id="poly-abc",
        question="Test?",
        kalshi_title="Test?",
        poly_title="Test?",
        kalshi_yes_ask=0.48,
        poly_no_ask=0.47,
        gross_spread=0.05,
        net_edge=0.03,
        settlement_match_score=0.9,
        settlement_flags=[],
        volume_kalshi=50000,
        volume_poly=50000,
        kelly_fraction=0.3,
    )
    defaults.update(kwargs)
    return ArbOpportunity(**defaults)


def test_m07_uses_redis_cache_avoids_http(tmp_path, monkeypatch):
    """When L2 cache has data, M07 never calls requests.get."""
    settings = Settings(
        SQLITE_PATH=tmp_path / "test.db",
        ALPACA_PAPER_TRADE=True,
        POLYMARKET_PAPER_TRADING_ENABLED=True,
        ARB_PAPER_RELAX_ORDERBOOK=False,
        ARB_MIN_NET_EDGE=0.01,
        KALSHI_MIN_VOLUME_24H=1000.0,
    )
    opp = _make_opp()

    cached_kalshi = {
        "yes": [[0.48, 500]],
        "no": [[0.52, 500]],
    }
    cached_poly = {
        "asks": [{"price": "0.47", "size": "500"}],
        "bids": [{"price": "0.53", "size": "500"}],
    }

    def read_side(venue, ticker, **kw):
        if venue == "POLY":
            return cached_poly
        if venue == "KALSHI":
            return cached_kalshi
        return {}

    monkeypatch.setattr(
        "apex.cache.orderbook_l2.read_orderbook",
        read_side,
    )
    monkeypatch.setattr(
        "apex.layers.l3.risk_checks._cached_kalshi_orderbook",
        lambda t: cached_kalshi,
    )
    mock_get = MagicMock()
    monkeypatch.setattr("apex.layers.l3.risk_checks.requests.get", mock_get)

    from apex.layers.l3.risk_checks import RiskCheckEngine

    engine = RiskCheckEngine(settings=settings)
    result = engine.run_arb_paper(opp, stake_usd=50.0)

    mock_get.assert_not_called()
    assert "M07" not in result.failed, f"M07 failed: {result.rejection_reason}"


def test_m07_falls_back_to_http_on_cache_miss(tmp_path, monkeypatch):
    """When cache is empty, M07 falls back to live HTTP."""
    settings = Settings(
        SQLITE_PATH=tmp_path / "test.db",
        ALPACA_PAPER_TRADE=True,
        POLYMARKET_PAPER_TRADING_ENABLED=True,
        ARB_PAPER_RELAX_ORDERBOOK=True,
        ARB_MIN_NET_EDGE=0.01,
        KALSHI_MIN_VOLUME_24H=1000.0,
    )
    opp = _make_opp()

    monkeypatch.setattr("apex.cache.orderbook_l2.read_orderbook", lambda *a, **k: {})
    monkeypatch.setattr(
        "apex.layers.l3.risk_checks._cached_kalshi_orderbook",
        lambda t: {"yes": [[0.48, 500]], "no": [[0.52, 500]]},
    )

    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "asks": [{"price": "0.47", "size": "500"}],
        "bids": [],
    }
    mock_get = MagicMock(return_value=mock_resp)
    monkeypatch.setattr("apex.layers.l3.risk_checks.requests.get", mock_get)

    from apex.layers.l3.risk_checks import RiskCheckEngine

    engine = RiskCheckEngine(settings=settings)
    engine.run_arb_paper(opp, stake_usd=50.0)

    mock_get.assert_called_once()
    assert "clob.polymarket.com" in mock_get.call_args[0][0]


def test_kalshi_ob_cache_is_thread_safe(monkeypatch):
    """_KALSHI_OB_CACHE writes do not race under concurrent access."""
    from apex.layers.l3 import risk_checks as rc_mod

    rc_mod._KALSHI_OB_CACHE.clear()
    call_count = 0

    def fake_fetch(ticker):
        nonlocal call_count
        call_count += 1
        return {"yes": [[0.5, 100]], "no": [[0.5, 100]]}

    monkeypatch.setattr(rc_mod, "fetch_kalshi_orderbook", fake_fetch)
    threads = [
        threading.Thread(target=rc_mod._cached_kalshi_orderbook, args=("KX-THREAD-TEST",))
        for _ in range(20)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert call_count <= 3
