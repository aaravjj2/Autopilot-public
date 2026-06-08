"""Quantitative decision engine for APEX Autopilot (no LLM required).

Implements the mathematical foundations used across ingestion, ranking, sizing,
and brain verdicts:

- Two-leg prediction-market arbitrage payoff and Kalshi fee model
- Fractional Kelly sizing under settlement uncertainty
- Composite execution score (shared with ``arb_ranking``)
- Pre-trade quality gates aligned to ``Settings``
- Calibrated action mapping (EXECUTE / REVIEW / SKIP) with explicit risk ledger
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from apex.services.arb_ranking import execution_score, min_leg_volume, passes_quality_gate

ENGINE_VERSION = "2026.05.2"
KALSHI_FEE_RATE = 0.07  # fee on YES-leg profit (Kalshi taker model used in arb_engine)
EXECUTE_SCORE_FLOOR = 0.08


@dataclass(frozen=True)
class QuantAnalysis:
    """Full quantitative breakdown for one arb opportunity."""

    gross_spread: float
    net_edge: float
    fee_component: float
    settlement_match_score: float
    min_leg_volume_usd: float
    vwap_edge: float
    settlement_flags: tuple[str, ...]
    execution_score: float
    effective_win_prob: float
    kelly_full: float
    kelly_fractional: float
    suggested_notional_usd: float
    gates_passed: bool
    gate_reason: str | None
    action: str
    confidence: float
    rationale: str
    risks: tuple[str, ...] = field(default_factory=tuple)
    formulas: tuple[str, ...] = field(default_factory=tuple)


def gross_spread(kalshi_yes_ask: float, poly_no_ask: float) -> float:
    """Gross locked-in edge before fees: 1 - (yes_ask + no_ask)."""
    return round(1.0 - kalshi_yes_ask - poly_no_ask, 6)


def kalshi_fee_on_yes_win(kalshi_yes_ask: float) -> float:
    """Kalshi fee charged on YES-leg profit at resolution."""
    return KALSHI_FEE_RATE * max(0.0, 1.0 - kalshi_yes_ask)


def net_edge_from_quotes(kalshi_yes_ask: float, poly_no_ask: float) -> float:
    """Net edge after Kalshi fee on the winning YES leg."""
    gross = gross_spread(kalshi_yes_ask, poly_no_ask)
    fee = kalshi_fee_on_yes_win(kalshi_yes_ask)
    return round(gross - fee, 6)


def effective_win_probability(settlement_score: float, flag_count: int) -> float:
    """Discount near-certainty arb by settlement confidence and flag count."""
    base = max(0.0, min(1.0, settlement_score))
    penalty = 0.08 * max(0, flag_count)
    return max(0.05, min(0.99, base - penalty))


def full_kelly_binary(*, win_prob: float, cost: float) -> float:
    """Kelly fraction for a binary $1 payoff with capital outlay ``cost``."""
    if cost <= 0.0 or cost >= 1.0:
        return 0.0
    b = (1.0 - cost) / cost  # net odds
    if b <= 0.0:
        return 0.0
    q = 1.0 - win_prob
    f = (win_prob * b - q) / b
    return max(0.0, min(1.0, f))


def fractional_kelly(
    *,
    win_prob: float,
    cost: float,
    alpha: float = 0.25,
) -> float:
    """Fractional Kelly (``alpha``) caps variance from model error."""
    return max(0.0, min(0.5, alpha * full_kelly_binary(win_prob=win_prob, cost=cost)))


def liquidity_notional_cap(
    min_vol: float,
    *,
    bankroll_usd: float,
    kelly_frac: float,
    participation_rate: float = 0.10,
) -> float:
    """Size cap: min of fractional-Kelly bankroll slice and thin-leg participation."""
    kelly_cap = bankroll_usd * kelly_frac
    liquidity_cap = max(0.0, min_vol) * participation_rate
    return max(0.0, min(kelly_cap, liquidity_cap))


def _confidence_from_score(score: float, gates_ok: bool) -> float:
    """Map execution score to [0,1] confidence; fails closed when gates fail."""
    if not gates_ok:
        return max(0.35, min(0.75, 0.5 + score))
    # Sigmoid centered near EXECUTE_SCORE_FLOOR.
    x = 6.0 * (score - EXECUTE_SCORE_FLOOR)
    return max(0.0, min(0.99, 1.0 / (1.0 + math.exp(-x))))


def _opp_like(facts: dict[str, Any]) -> Any:
    """Minimal duck-type object for arb_ranking helpers."""

    class _Opp:
        pass

    o = _Opp()
    for k, v in facts.items():
        setattr(o, k, v)
    return o


def evaluate_opportunity(
    facts: dict[str, Any],
    settings: Any | None = None,
) -> QuantAnalysis:
    """Run full quantitative pipeline and return an auditable analysis."""
    if settings is None:
        from apex.core.config import get_settings

        settings = get_settings()

    yes_ask = float(facts.get("kalshi_yes_ask") or 0.0)
    no_ask = float(facts.get("poly_no_ask") or 0.0)
    if facts.get("net_edge") is None:
        net = net_edge_from_quotes(yes_ask, no_ask)
    else:
        net = float(facts["net_edge"])
    if facts.get("gross_spread") is None:
        gross = gross_spread(yes_ask, no_ask)
    else:
        gross = float(facts["gross_spread"])
    fee = round(gross - net, 6)
    settle = float(facts.get("settlement_match_score") or 0.0)
    flags_raw = facts.get("settlement_flags") or []
    flags = tuple(str(f) for f in flags_raw) if isinstance(flags_raw, list) else ()
    vwap = float(facts.get("vwap_edge") or 0.0)
    min_vol = min(
        float(facts.get("volume_kalshi") or 0.0),
        float(facts.get("volume_poly") or 0.0),
    )
    cost = yes_ask + no_ask
    win_p = effective_win_probability(settle, len(flags))
    kelly_full = full_kelly_binary(win_prob=win_p, cost=cost)
    kelly_frac = fractional_kelly(
        win_prob=win_p,
        cost=cost,
        alpha=float(getattr(settings, "kelly_alpha", 0.25)),
    )
    bankroll = float(getattr(settings, "kalshi_paper_bankroll_usd", 5000.0))
    notional = liquidity_notional_cap(min_vol, bankroll_usd=bankroll, kelly_frac=kelly_frac)

    opp = _opp_like(
        {
            **facts,
            "net_edge": net,
            "settlement_match_score": settle,
            "settlement_flags": list(flags),
            "volume_kalshi": facts.get("volume_kalshi", 0),
            "volume_poly": facts.get("volume_poly", 0),
            "vwap_edge": vwap,
        }
    )
    score = execution_score(opp)
    gates_ok, gate_reason = passes_quality_gate(opp, settings)

    min_edge = float(getattr(settings, "arb_min_net_edge", 0.02))
    risks: list[str] = []
    if net <= 0:
        risks.append("non-positive net edge after fees")
    if settle < float(getattr(settings, "arb_exec_min_settlement_score", 0.55)):
        risks.append("settlement match below gate")
    if min_vol < float(getattr(settings, "arb_exec_min_leg_volume_usd", 2000.0)):
        risks.append(f"thin min-leg liquidity (~${min_vol:,.0f} 24h)")
    if flags:
        risks.append(f"{len(flags)} settlement flag(s): {', '.join(flags[:3])}")
    if vwap and vwap <= 0:
        risks.append("VWAP book walk shows non-positive executable edge")

    formulas = (
        "gross = 1 - (yes_ask + no_ask)",
        f"fee = {KALSHI_FEE_RATE} * (1 - yes_ask)",
        "net_edge = gross - fee",
        "f* = (p*b - q) / b,  b = (1-cost)/cost,  cost = yes_ask + no_ask",
        f"fractional_kelly = {getattr(settings, 'kelly_alpha', 0.25)} * f*",
        "execution_score = edge + 0.25*settlement + 0.15*log1p(min_vol)/15 + vwap_bonus - 0.05*flags",
    )

    if not gates_ok or net < min_edge or net <= 0:
        action = "SKIP"
        rationale = (
            f"Fails quality gate ({gate_reason or 'edge_floor'}): "
            f"net={net:.2%}, settlement={settle:.2f}, min_vol=${min_vol:,.0f}."
        )
    elif (
        score >= EXECUTE_SCORE_FLOOR
        and net >= max(min_edge, 0.03)
        and settle >= 0.80
        and not flags
        and min_vol >= float(getattr(settings, "arb_exec_min_leg_volume_usd", 2000.0)) * 5
    ):
        action = "EXECUTE"
        rationale = (
            f"Quant EXECUTE: score={score:.3f}, net={net:.2%}, settlement={settle:.2f}, "
            f"Kelly_f={kelly_frac:.3f}, notional_cap≈${notional:,.0f}."
        )
    else:
        action = "REVIEW"
        rationale = (
            f"Marginal quant signal: score={score:.3f}, net={net:.2%}, "
            f"settlement={settle:.2f}; human/secondary check advised."
        )

    confidence = _confidence_from_score(score, gates_ok and net >= min_edge)

    return QuantAnalysis(
        gross_spread=gross,
        net_edge=net,
        fee_component=fee,
        settlement_match_score=settle,
        min_leg_volume_usd=min_vol,
        vwap_edge=vwap,
        settlement_flags=flags,
        execution_score=score,
        effective_win_prob=win_p,
        kelly_full=kelly_full,
        kelly_fractional=kelly_frac,
        suggested_notional_usd=notional,
        gates_passed=gates_ok and net >= min_edge,
        gate_reason=gate_reason,
        action=action,
        confidence=confidence,
        rationale=rationale,
        risks=tuple(risks),
        formulas=formulas,
    )


def analysis_to_verdict_dict(analysis: QuantAnalysis) -> dict[str, Any]:
    """Serialize for API / audit logs."""
    return {
        "action": analysis.action,
        "confidence": round(analysis.confidence, 4),
        "rationale": analysis.rationale,
        "risks": list(analysis.risks),
        "source": "quant",
        "engine_version": ENGINE_VERSION,
        "execution_score": round(analysis.execution_score, 4),
        "kelly_fractional": round(analysis.kelly_fractional, 4),
        "suggested_notional_usd": round(analysis.suggested_notional_usd, 2),
        "effective_win_prob": round(analysis.effective_win_prob, 4),
        "formulas": list(analysis.formulas),
    }


def explain_topic(query: str) -> str:
    """Deterministic math/strategy explainer for offline ``ask()`` responses."""
    q = query.lower()
    lines = [f"APEX Quant Engine v{ENGINE_VERSION}", ""]
    if any(t in q for t in ("kelly", "size", "sizing", "bankroll")):
        lines += [
            "Fractional Kelly (binary arb):",
            "  cost = yes_ask + no_ask",
            "  b = (1 - cost) / cost",
            "  f* = (p*b - (1-p)) / b",
            "  f_trade = alpha * f*  (alpha = KELLY_ALPHA, default 0.25)",
            "  notional_cap = min(bankroll * f_trade, 0.10 * min_leg_volume)",
        ]
    if any(t in q for t in ("edge", "arb", "spread", "fee")):
        lines += [
            "Two-leg arb edge:",
            "  gross = 1 - (kalshi_yes_ask + poly_no_ask)",
            f"  fee = {KALSHI_FEE_RATE} * (1 - kalshi_yes_ask)",
            "  net_edge = gross - fee",
        ]
    if any(t in q for t in ("rank", "score", "priority", "execution")):
        lines += [
            "Execution score (ranking):",
            "  score = edge + 0.25*settlement + 0.15*log1p(min_vol)/15",
            "          + (0.10 if vwap_edge>0 else 0) - 0.05*len(flags)",
        ]
    if any(t in q for t in ("gate", "risk", "skip")):
        lines += [
            "Pre-trade gates (fail-closed):",
            "  settlement >= ARB_EXEC_MIN_SETTLEMENT_SCORE",
            "  min_leg_volume >= ARB_EXEC_MIN_LEG_VOLUME_USD",
            "  len(flags) <= ARB_EXEC_MAX_SETTLEMENT_FLAGS",
            "  net_edge >= ARB_MIN_NET_EDGE",
        ]
    if len(lines) <= 2:
        lines += [
            "Core pipeline: ingest quotes → match settlement → net edge & fees",
            "→ execution score → quality gates → fractional Kelly size → risk checks → paper execute.",
        ]
    return "\n".join(lines)
