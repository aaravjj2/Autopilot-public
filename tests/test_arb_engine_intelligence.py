from __future__ import annotations
# BRIGHTDATA INTEGRATION — 2026-05-27 — arb engine intelligence tests

from apex.core.config import Settings
from apex.domain.models import ArbOpportunity
from apex.services.arb_engine import ArbEngine, _intelligence_cache


def _opp(ticker: str = "K1", edge: float = 0.05) -> ArbOpportunity:
    return ArbOpportunity(
        kalshi_ticker=ticker,
        poly_market_id="p1",
        question="q",
        kalshi_title="k",
        poly_title="p",
        kalshi_yes_ask=0.4,
        poly_no_ask=0.5,
        gross_spread=0.1,
        net_edge=edge,
        settlement_match_score=0.9,
        settlement_flags=[],
    )


def test_risk_signal_reduces_net_edge() -> None:
    class _Intel:
        async def check_session_budget(self):
            return {"ok": True}

        async def get_market_context(self, *_args, **_kwargs):
            return {"risk_signals": ["postponed"]}

    engine = ArbEngine(settings=Settings(alpaca_paper_trade=True), store=None, intelligence=_Intel())  # type: ignore[arg-type]
    opp = _opp()
    engine._apply_intelligence_context([opp])
    assert opp.net_edge == 0.045


def test_budget_exhausted_skips_intelligence() -> None:
    calls = {"n": 0}

    class _Intel:
        async def check_session_budget(self):
            return {"ok": False}

        async def get_market_context(self, *_args, **_kwargs):
            calls["n"] += 1
            return {}

    engine = ArbEngine(settings=Settings(alpaca_paper_trade=True), store=None, intelligence=_Intel())  # type: ignore[arg-type]
    engine._apply_intelligence_context([_opp()])
    assert calls["n"] == 0


def test_intelligence_cache_prevents_duplicate_calls() -> None:
    _intelligence_cache.clear()
    calls = {"n": 0}

    class _Intel:
        async def check_session_budget(self):
            return {"ok": True}

        async def get_market_context(self, *_args, **_kwargs):
            calls["n"] += 1
            return {"risk_signals": []}

    engine = ArbEngine(settings=Settings(alpaca_paper_trade=True), store=None, intelligence=_Intel())  # type: ignore[arg-type]
    engine._apply_intelligence_context([_opp("K1"), _opp("K1")])
    assert calls["n"] == 1


def test_no_intelligence_scan_unchanged() -> None:
    engine = ArbEngine(settings=Settings(alpaca_paper_trade=True), store=None, intelligence=None)  # type: ignore[arg-type]
    opp = _opp()
    old_edge = opp.net_edge
    engine._apply_intelligence_context([opp])
    assert opp.net_edge == old_edge
