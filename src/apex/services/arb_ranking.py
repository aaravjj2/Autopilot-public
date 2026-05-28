"""Execution-quality ranking and a pre-trade quality gate for arb opportunities.

Ranking by raw ``net_edge`` alone over-weights opportunities that may be thin,
loosely matched, or carry settlement-mismatch risk. These helpers combine edge
with settlement confidence, leg liquidity, executable (VWAP) edge, and a penalty
for settlement flags so the autopilot spends its limited per-cycle trade budget
on the highest-quality edges first. The quality gate then drops opportunities
that clear the edge threshold but are too risky/illiquid to execute.
"""

from __future__ import annotations

import math
from typing import Any

from apex.core.config import Settings


def _f(opp: Any, name: str, default: float = 0.0) -> float:
    try:
        return float(getattr(opp, name, default) or default)
    except (TypeError, ValueError):
        return default


def min_leg_volume(opp: Any) -> float:
    """Conservative liquidity proxy: the smaller of the two legs' 24h volume."""
    return min(_f(opp, "volume_kalshi"), _f(opp, "volume_poly"))


def execution_score(opp: Any) -> float:
    """Composite quality score (higher is better) used to rank execution order.

    Dominated by net edge, then rewarded for settlement confidence, liquidity,
    and a confirmed executable VWAP edge; penalized per settlement flag.
    """
    edge = _f(opp, "net_edge")
    settlement = _f(opp, "settlement_match_score")
    liquidity = min_leg_volume(opp)
    vwap_edge = _f(opp, "vwap_edge")
    flags = getattr(opp, "settlement_flags", None) or []

    # log1p compresses liquidity so a whale market does not dwarf edge entirely.
    liquidity_term = math.log1p(max(0.0, liquidity)) / 15.0  # ~0..1 for 0..3M
    vwap_bonus = 0.10 if vwap_edge and vwap_edge > 0 else 0.0
    flag_penalty = 0.05 * len(flags)

    return (
        (1.00 * edge)
        + (0.25 * settlement)
        + (0.15 * liquidity_term)
        + vwap_bonus
        - flag_penalty
    )


def rank_for_execution(opps: list[Any]) -> list[Any]:
    """Return opportunities ordered best-first by composite execution score."""
    return sorted(opps, key=execution_score, reverse=True)


def passes_quality_gate(opp: Any, settings: Settings) -> tuple[bool, str | None]:
    """Pre-trade gate enforcing minimum settlement confidence, leg liquidity,
    and a cap on settlement flags. Returns (ok, reason_if_rejected)."""
    settlement = _f(opp, "settlement_match_score")
    if settlement < float(settings.arb_exec_min_settlement_score):
        return False, f"settlement_score<{settings.arb_exec_min_settlement_score}"

    liquidity = min_leg_volume(opp)
    if liquidity < float(settings.arb_exec_min_leg_volume_usd):
        return False, f"leg_volume<{settings.arb_exec_min_leg_volume_usd}"

    flags = getattr(opp, "settlement_flags", None) or []
    if len(flags) > int(settings.arb_exec_max_settlement_flags):
        return False, f"settlement_flags>{settings.arb_exec_max_settlement_flags}"

    return True, None
