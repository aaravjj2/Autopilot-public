"""IV to risk-neutral probability (Week 3 Day 2)."""

from __future__ import annotations

import math


def iv_to_probability(iv: float, days_to_expiry: float, *, rfr: float = 0.05) -> float:
    """Rough ATM digital probability from annualized IV."""
    if days_to_expiry <= 0 or iv <= 0:
        return 0.5
    t = days_to_expiry / 365.0
    # Simplified: P(up) ~ N(d2) approximation for ATM
    d2 = (-(rfr - 0.5 * iv * iv) * t) / (iv * math.sqrt(t))
    return max(0.01, min(0.99, 0.5 * (1 + math.erf(d2 / math.sqrt(2)))))
