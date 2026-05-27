"""Fractional Kelly with VIX volatility dampener (Week 6 Day 1)."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class KellyInput:
    """Inputs for f* = (bp - q) / b * alpha * exp(-lambda * VIX)."""

    win_prob: float  # p
    decimal_odds: float  # e.g. 2.0 for even money -> b = 1.0
    alpha: float = 0.25  # quarter-Kelly
    vix: float = 20.0
    lambda_dampener: float = 0.02


@dataclass
class KellyResult:
    raw_fraction: float
    dampened_fraction: float
    vix_multiplier: float


def fractional_kelly(inp: KellyInput) -> KellyResult:
    """
    f* = ((b*p - q) / b) * alpha * exp(-lambda * VIX)
    where b = decimal_odds - 1, q = 1 - p.
    """
    p = max(0.0, min(1.0, inp.win_prob))
    q = 1.0 - p
    b = max(inp.decimal_odds - 1.0, 1e-6)
    raw = (b * p - q) / b
    raw = max(0.0, raw)
    vix_mult = math.exp(-inp.lambda_dampener * max(0.0, inp.vix))
    dampened = raw * inp.alpha * vix_mult
    return KellyResult(
        raw_fraction=round(raw, 6),
        dampened_fraction=round(min(dampened, 1.0), 6),
        vix_multiplier=round(vix_mult, 6),
    )


def kelly_from_edge(
    net_edge: float,
    *,
    ai_confidence: float = 0.7,
    alpha: float = 0.25,
    vix: float = 20.0,
    lambda_dampener: float = 0.02,
) -> KellyResult:
    """Map arb net_edge + confidence into Kelly sizing."""
    p = min(0.95, max(0.55, 0.5 + net_edge * ai_confidence * 2))
    odds = 1.0 + max(net_edge * 3, 0.08)
    return fractional_kelly(
        KellyInput(
            win_prob=p,
            decimal_odds=odds,
            alpha=alpha,
            vix=vix,
            lambda_dampener=lambda_dampener,
        )
    )
