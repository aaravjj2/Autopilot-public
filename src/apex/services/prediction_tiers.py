"""Confidence tiers and EV-Kelly sizing for prediction-market paper execution.

Patterns inspired by erickdronski/kalshi-polymarket-trader: tiered confidence gates
with empirical LOW-tier kill, and fractional Kelly stake caps.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math

from apex.core.config import Settings, get_settings


class ConfidenceTier(str, Enum):
    """Model-confidence bands for prediction-market execution."""

    HIGH = "HIGH"  # >= 0.85 — trade at 2× base Kelly stake
    MID = "MID"  # 0.75–0.85 — trade at 1× base Kelly stake
    LOW = "LOW"  # < 0.75 — killed (empirically sub-profitable)


# Tier stake multipliers (HIGH 2×, MID 1×, LOW killed).
_TIER_ALLOCATION: dict[ConfidenceTier, float] = {
    ConfidenceTier.HIGH: 2.0,
    ConfidenceTier.MID: 1.0,
    ConfidenceTier.LOW: 0.0,
}

_HIGH_THRESHOLD = 0.85
_MID_THRESHOLD = 0.75
_MIN_STAKE_USD = 10.0


def classify_confidence(model_confidence: float) -> ConfidenceTier:
    """Map model confidence [0,1] to execution tier."""
    c = float(model_confidence)
    if c >= _HIGH_THRESHOLD:
        return ConfidenceTier.HIGH
    if c >= _MID_THRESHOLD:
        return ConfidenceTier.MID
    return ConfidenceTier.LOW


def ev_kelly_stake(
    edge: float,
    fair_prob: float,
    bankroll: float,
    kelly_cap: float = 0.25,
) -> float:
    """Fractional Kelly stake (USD) from model edge and fair probability.

    Uses binary YES Kelly: f* = |edge| / (1 - market_prob) with market_prob
    inferred as fair_prob - edge, then scales by ``kelly_cap`` (quarter-Kelly default).
    """
    if bankroll <= 0 or kelly_cap <= 0:
        return 0.0

    eff_edge = abs(float(edge))
    if eff_edge <= 0:
        return 0.0

    fair = max(0.01, min(0.99, float(fair_prob)))
    market_prob = max(0.01, min(0.99, fair - float(edge)))

    kelly_fraction = eff_edge / (1.0 - market_prob)
    kelly_fraction = min(kelly_fraction, 1.0)

    stake = bankroll * kelly_fraction * float(kelly_cap)
    max_stake = bankroll * float(kelly_cap)
    stake = max(_MIN_STAKE_USD, min(stake, max_stake))
    return round(stake, 2)


def should_execute(
    tier: ConfidenceTier,
    edge: float,
    min_edge: float = 0.05,
) -> bool:
    """Return True when tier is tradable and |edge| meets minimum."""
    if tier is ConfidenceTier.LOW:
        return False
    return abs(float(edge)) >= float(min_edge)


@dataclass(frozen=True)
class PredictionSignal:
    fair_prob: float
    market_prob: float
    edge: float
    tier: ConfidenceTier
    suggested_stake_usd: float


def tier_allocation_multiplier(tier: ConfidenceTier) -> float:
    return _TIER_ALLOCATION.get(tier, 0.0)


def build_prediction_signal(
    row: dict,
    *,
    settings: Settings | None = None,
    bankroll: float | None = None,
    min_edge: float | None = None,
    kelly_cap: float | None = None,
) -> PredictionSignal | None:
    """Build a sized signal from a scored opportunity row, or None if filtered."""
    settings = settings or get_settings()
    edge = float(row.get("model_edge") or 0)
    fair_prob = float(row.get("fair_prob") or 0.5)
    if not math.isfinite(edge) or not math.isfinite(fair_prob):
        return None
    market_prob = float(
        row.get("market_yes_ask")
        or row.get("market_implied")
        or (fair_prob - edge)
    )
    if not math.isfinite(market_prob):
        return None
    market_prob = max(0.01, min(0.99, market_prob))
    model_confidence = float(row.get("model_confidence") or 0)
    if not math.isfinite(model_confidence):
        return None
    tier = classify_confidence(model_confidence)

    min_e = float(min_edge if min_edge is not None else settings.world_cup_min_model_edge)
    if not should_execute(tier, edge, min_edge=min_e):
        return None

    br = float(bankroll if bankroll is not None else settings.polymarket_paper_bankroll_usd)
    cap = float(kelly_cap if kelly_cap is not None else settings.kelly_alpha)
    base_stake = ev_kelly_stake(edge, fair_prob, br, kelly_cap=cap)
    stake = round(base_stake * tier_allocation_multiplier(tier), 2)

    return PredictionSignal(
        fair_prob=fair_prob,
        market_prob=market_prob,
        edge=edge,
        tier=tier,
        suggested_stake_usd=stake,
    )


def bankroll_for_venue(settings: Settings, venue: str | None) -> float:
    """Paper bankroll for a single-venue World Cup leg."""
    if venue == "kalshi":
        return float(settings.kalshi_paper_bankroll_usd)
    return float(settings.polymarket_paper_bankroll_usd)
