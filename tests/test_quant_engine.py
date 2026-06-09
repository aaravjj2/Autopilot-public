"""Unit tests for the offline quantitative decision engine."""

from __future__ import annotations

import pytest

from apex.brain import quant_engine as qe


def _facts(**kw):
    base = dict(
        net_edge=0.05,
        gross_spread=0.1,
        settlement_match_score=0.9,
        settlement_flags=[],
        volume_kalshi=20000.0,
        volume_poly=20000.0,
        kalshi_yes_ask=0.4,
        poly_no_ask=0.45,
    )
    base.update(kw)
    return base


def test_net_edge_matches_fee_model() -> None:
    yes, no = 0.42, 0.50
    gross = qe.gross_spread(yes, no)
    fee = qe.kalshi_fee_on_yes_win(yes)
    net = qe.net_edge_from_quotes(yes, no)
    assert net == pytest.approx(gross - fee, abs=1e-6)


@pytest.mark.smoke
def test_fractional_kelly_produces_valid_sizes() -> None:
    f = qe.fractional_kelly(win_prob=0.9, cost=0.85, alpha=0.25)
    assert 0.0 <= f <= 0.5


def test_evaluate_executes_clean_opportunity() -> None:
    a = qe.evaluate_opportunity(_facts())
    assert a.action == "EXECUTE"
    assert a.gates_passed is True
    assert a.execution_score >= qe.EXECUTE_SCORE_FLOOR
    assert a.kelly_fractional > 0.0


def test_evaluate_skips_thin_liquidity() -> None:
    a = qe.evaluate_opportunity(_facts(volume_poly=500.0))
    assert a.action == "SKIP"
    assert not a.gates_passed


def test_evaluate_reviews_marginal() -> None:
    a = qe.evaluate_opportunity(
        _facts(net_edge=0.025, settlement_match_score=0.7, volume_kalshi=6000, volume_poly=6000)
    )
    assert a.action == "REVIEW"


def test_analysis_to_verdict_dict_has_engine_version() -> None:
    a = qe.evaluate_opportunity(_facts())
    d = qe.analysis_to_verdict_dict(a)
    assert d["source"] == "quant"
    assert d["engine_version"] == qe.ENGINE_VERSION
    assert "formulas" in d


def test_explain_topic_covers_kelly() -> None:
    text = qe.explain_topic("How do I size with Kelly?")
    assert "Kelly" in text or "kelly" in text.lower()
    assert qe.ENGINE_VERSION in text
