"""Tests for execution-quality ranking and the pre-trade quality gate."""

from __future__ import annotations

from apex.core.config import Settings
from apex.domain.models import ArbOpportunity
from apex.services.arb_ranking import (
    execution_score,
    min_leg_volume,
    passes_quality_gate,
    rank_for_execution,
)


def _opp(**kw) -> ArbOpportunity:
    base = dict(
        kalshi_ticker="KX",
        poly_market_id="pm",
        question="q",
        kalshi_title="q",
        poly_title="q",
        kalshi_yes_ask=0.40,
        poly_no_ask=0.45,
        gross_spread=0.10,
        net_edge=0.05,
        settlement_match_score=0.90,
        settlement_flags=[],
        volume_kalshi=20000.0,
        volume_poly=20000.0,
    )
    base.update(kw)
    return ArbOpportunity(**base)


def test_min_leg_volume_uses_smaller_leg() -> None:
    opp = _opp(volume_kalshi=50000.0, volume_poly=1500.0)
    assert min_leg_volume(opp) == 1500.0


def test_higher_settlement_and_liquidity_ranks_higher_at_equal_edge() -> None:
    weak = _opp(net_edge=0.05, settlement_match_score=0.60, volume_kalshi=3000, volume_poly=3000)
    strong = _opp(net_edge=0.05, settlement_match_score=0.95, volume_kalshi=80000, volume_poly=80000)
    assert execution_score(strong) > execution_score(weak)
    assert rank_for_execution([weak, strong])[0] is strong


def test_settlement_flags_penalize_score() -> None:
    clean = _opp(settlement_flags=[])
    flagged = _opp(settlement_flags=["A", "B"])
    assert execution_score(clean) > execution_score(flagged)


def test_quality_gate_blocks_low_settlement() -> None:
    s = Settings(alpaca_paper_trade=True, arb_exec_min_settlement_score=0.55)
    ok, reason = passes_quality_gate(_opp(settlement_match_score=0.40), s)
    assert ok is False
    assert reason and "settlement_score" in reason


def test_quality_gate_blocks_thin_liquidity() -> None:
    s = Settings(alpaca_paper_trade=True, arb_exec_min_leg_volume_usd=2000.0)
    ok, reason = passes_quality_gate(_opp(volume_kalshi=500, volume_poly=500), s)
    assert ok is False
    assert reason and "leg_volume" in reason


def test_quality_gate_blocks_too_many_flags() -> None:
    s = Settings(alpaca_paper_trade=True, arb_exec_max_settlement_flags=2)
    ok, reason = passes_quality_gate(_opp(settlement_flags=["a", "b", "c"]), s)
    assert ok is False
    assert reason and "settlement_flags" in reason


def test_quality_gate_passes_clean_opp() -> None:
    s = Settings(alpaca_paper_trade=True)
    ok, reason = passes_quality_gate(_opp(), s)
    assert ok is True
    assert reason is None
