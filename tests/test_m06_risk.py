"""M06 daily arb loss limit (Phase 3)."""

from __future__ import annotations

from apex.core.config import Settings
from apex.domain.models import ArbOpportunity
from apex.layers.l3.risk_checks import RiskCheckEngine


def _opp() -> ArbOpportunity:
    return ArbOpportunity(
        kalshi_ticker="KX-T",
        poly_market_id="tok",
        question="q",
        kalshi_title="k",
        poly_title="p",
        kalshi_yes_ask=0.45,
        poly_no_ask=0.48,
        gross_spread=0.07,
        net_edge=0.05,
        settlement_match_score=0.9,
        settlement_flags=[],
        volume_kalshi=1e6,
        volume_poly=1e6,
    )


def test_m06_passes_under_cap(tmp_path, monkeypatch):
    settings = Settings(
        SQLITE_PATH=tmp_path / "audit.db",
        ALPACA_PAPER_TRADE=True,
        POLYMARKET_PAPER_TRADING_ENABLED=True,
        ARB_MAX_DAILY_LOSS_USD=500.0,
        ARB_PAPER_RELAX_ORDERBOOK=True,
    )
    monkeypatch.setattr(
        "apex.layers.l3.risk_checks.fetch_kalshi_orderbook",
        lambda t: {"yes": [[0.5, 1000]], "no": [[0.5, 1000]]},
    )
    monkeypatch.setattr(
        "apex.layers.l3.risk_checks.requests.get",
        lambda *a, **k: type("R", (), {"ok": True, "raise_for_status": lambda s: None, "json": lambda s: {"asks": [[{"price": "0.5", "size": "1000"}]]}})(),
    )
    engine = RiskCheckEngine(settings)
    result = engine.run_arb_paper(_opp(), stake_usd=50.0)
    assert "M06" in str(result.passed) or result.all_passed or not result.failed
