"""Table-driven tests for prediction tier gating and EV-Kelly sizing."""

from __future__ import annotations

import pytest

from apex.core.config import Settings
from apex.services.prediction_tiers import (
    ConfidenceTier,
    PredictionSignal,
    build_prediction_signal,
    classify_confidence,
    ev_kelly_stake,
    should_execute,
    tier_allocation_multiplier,
)


@pytest.mark.parametrize(
    ("model_confidence", "expected"),
    [
        (0.90, ConfidenceTier.HIGH),
        (0.85, ConfidenceTier.HIGH),
        (0.849, ConfidenceTier.MID),
        (0.75, ConfidenceTier.MID),
        (0.749, ConfidenceTier.LOW),
        (0.0, ConfidenceTier.LOW),
    ],
)
def test_classify_confidence(model_confidence: float, expected: ConfidenceTier) -> None:
    assert classify_confidence(model_confidence) is expected


@pytest.mark.parametrize(
    ("tier", "edge", "min_edge", "expected"),
    [
        (ConfidenceTier.HIGH, 0.06, 0.05, True),
        (ConfidenceTier.HIGH, 0.04, 0.05, False),
        (ConfidenceTier.MID, 0.05, 0.05, True),
        (ConfidenceTier.MID, -0.06, 0.05, True),
        (ConfidenceTier.LOW, 0.20, 0.05, False),
        (ConfidenceTier.LOW, 0.0, 0.0, False),
    ],
)
def test_should_execute(
    tier: ConfidenceTier,
    edge: float,
    min_edge: float,
    expected: bool,
) -> None:
    assert should_execute(tier, edge, min_edge=min_edge) is expected


@pytest.mark.parametrize(
    ("edge", "fair_prob", "bankroll", "kelly_cap", "min_stake"),
    [
        (0.10, 0.60, 10_000.0, 0.25, 10.0),
        (0.0, 0.60, 10_000.0, 0.25, 0.0),
        (0.10, 0.60, 0.0, 0.25, 0.0),
        (0.10, 0.60, 10_000.0, 0.0, 0.0),
    ],
)
def test_ev_kelly_stake(
    edge: float,
    fair_prob: float,
    bankroll: float,
    kelly_cap: float,
    min_stake: float,
) -> None:
    stake = ev_kelly_stake(edge, fair_prob, bankroll, kelly_cap=kelly_cap)
    if min_stake == 0.0:
        assert stake == 0.0
    else:
        assert stake >= min_stake
        assert stake <= bankroll * kelly_cap


def test_ev_kelly_stake_scales_with_edge() -> None:
    small = ev_kelly_stake(0.05, 0.55, 5000.0, kelly_cap=0.25)
    large = ev_kelly_stake(0.15, 0.65, 5000.0, kelly_cap=0.25)
    assert large > small


@pytest.mark.parametrize(
    ("tier", "mult"),
    [
        (ConfidenceTier.HIGH, 2.0),
        (ConfidenceTier.MID, 1.0),
        (ConfidenceTier.LOW, 0.0),
    ],
)
def test_tier_allocation_multiplier(tier: ConfidenceTier, mult: float) -> None:
    assert tier_allocation_multiplier(tier) == mult


@pytest.mark.parametrize(
    ("row", "expect_signal"),
    [
        (
            {
                "model_edge": 0.08,
                "fair_prob": 0.58,
                "market_yes_ask": 0.50,
                "model_confidence": 0.90,
            },
            True,
        ),
        (
            {
                "model_edge": 0.08,
                "fair_prob": 0.58,
                "market_yes_ask": 0.50,
                "model_confidence": 0.70,
            },
            False,
        ),
        (
            {
                "model_edge": 0.01,
                "fair_prob": 0.51,
                "market_yes_ask": 0.50,
                "model_confidence": 0.88,
            },
            False,
        ),
    ],
)
def test_build_prediction_signal(row: dict, expect_signal: bool) -> None:
    settings = Settings(
        world_cup_min_model_edge=0.03,
        kelly_alpha=0.25,
        polymarket_paper_bankroll_usd=5000.0,
    )
    sig = build_prediction_signal(row, settings=settings, min_edge=0.05)
    if expect_signal:
        assert isinstance(sig, PredictionSignal)
        assert sig.tier is ConfidenceTier.HIGH
        assert sig.suggested_stake_usd > 0
    else:
        assert sig is None


def test_high_tier_doubles_stake_vs_mid() -> None:
    settings = Settings(
        world_cup_min_model_edge=0.03,
        kelly_alpha=0.25,
        polymarket_paper_bankroll_usd=5000.0,
    )
    base_row = {
        "model_edge": 0.10,
        "fair_prob": 0.60,
        "market_yes_ask": 0.50,
    }
    high = build_prediction_signal(
        {**base_row, "model_confidence": 0.90}, settings=settings, min_edge=0.05
    )
    mid = build_prediction_signal(
        {**base_row, "model_confidence": 0.80}, settings=settings, min_edge=0.05
    )
    assert high is not None and mid is not None
    assert high.suggested_stake_usd == pytest.approx(mid.suggested_stake_usd * 2.0)
