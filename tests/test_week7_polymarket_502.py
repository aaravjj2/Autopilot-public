"""Polymarket 502 timeout handling (Week 7 Day 4)."""

from unittest.mock import patch

import pytest


def test_polymarket_book_502_returns_failure():
    import requests
    from apex.layers.l3 import risk_checks

    class FakeResp:
        status_code = 502

        def raise_for_status(self):
            raise requests.HTTPError("502")

        def json(self):
            return {}

    opp = type(
        "Opp",
        (),
        {
            "kalshi_ticker": "KX-T",
            "poly_market_id": "tok",
            "net_edge": 0.1,
            "kalshi_yes_ask": 0.45,
            "poly_no_ask": 0.48,
            "volume_kalshi": 1e6,
            "volume_poly": 1e6,
            "settlement_match_score": 0.9,
            "settlement_flags": "[]",
        },
    )()

    settings = type(
        "S",
        (),
        {
            "alpaca_paper_trade": True,
            "polymarket_paper_trading_enabled": True,
            "arb_min_net_edge": 0.01,
            "kalshi_min_volume_24h": 100,
            "kelly_alpha": 0.25,
            "kelly_lambda": 0.02,
            "cftc_contract_limit_usd": 250_000,
            "arb_paper_relax_orderbook": False,
        },
    )()

    engine = risk_checks.RiskCheckEngine(settings=settings)

    with patch.object(risk_checks, "fetch_kalshi_orderbook", return_value={"yes": [[0.5, 100]], "no": [[0.5, 100]]}):
        with patch("requests.get", return_value=FakeResp()):
            result = engine.run_arb_paper(opp, stake_usd=50.0)
    assert not result.all_passed
    assert "M07" in (result.rejection_reason or "")
