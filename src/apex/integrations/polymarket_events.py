"""
Polymarket *event* contracts: proposal building from public Gamma rows.

Separate from Alpaca equity/options — uses ``Instrument.POLYMARKET_EVENT`` only.
"""

from __future__ import annotations

from typing import Any

from apex.core.config import Settings
from apex.domain.enums import Direction, Instrument
from apex.domain.models import TradeProposal
from apex.integrations.polymarket_gamma_public import market_primary_id, yes_implied_probability


def _volume_of(market: dict[str, Any]) -> float:
    try:
        return float(market.get("volume", 0) or market.get("volumeNum", 0) or market.get("volume24hr", 0) or 0)
    except (TypeError, ValueError):
        return 0.0


def polymarket_event_proposal_from_market(
    market: dict[str, Any],
    settings: Settings,
) -> TradeProposal | None:
    """
    Build a paper-trade ``TradeProposal`` from a raw Gamma market dict.

    Policy ``polymarket_event_policy``:
    - ``underdog_bins``: lean YES when implied YES is low; lean NO when high.
    """
    if not settings.polymarket_paper_trading_enabled:
        return None
    vol = _volume_of(market)
    if vol < float(settings.polymarket_event_min_volume_24h):
        return None

    mid = market_primary_id(market)
    question = str(market.get("question") or market.get("title") or "")[:500]
    yes_p = yes_implied_probability(market)
    edge = abs(0.5 - yes_p)
    if edge < float(settings.polymarket_event_min_edge):
        return None

    stake = min(
        float(settings.polymarket_paper_default_stake_usd),
        float(settings.polymarket_paper_max_order_usd),
    )
    if stake < 1.0:
        return None

    policy = (settings.polymarket_event_policy or "underdog_bins").strip().lower()
    side: str | None = None
    direction = Direction.LONG

    if policy == "underdog_bins":
        if 0.08 <= yes_p <= 0.42:
            side = "YES"
        elif 0.58 <= yes_p <= 0.92:
            side = "NO"
        else:
            return None
    else:
        return None

    slug = str(market.get("slug") or mid)[:120]
    rationale = (
        f"PM public Gamma | policy={policy} | yes_implied={yes_p:.3f} | vol={vol:.0f} | "
        f"edge_vs_fifty={edge:.3f}"
    )[:2800]

    return TradeProposal(
        symbol=f"PM-EVT-{slug}",
        direction=direction,
        instrument=Instrument.POLYMARKET_EVENT,
        entry_price=max(0.01, min(0.99, yes_p)),
        position_size_pct=1.0,
        stop_loss=0.01,
        take_profit=0.99,
        max_loss_dollars=max(1.0, stake),
        conviction_final=max(7.0, float(settings.conviction_floor) + 0.01),
        judge_rationale=rationale,
        dissenting_view="automated_from_public_gamma",
        sector="POLYMARKET",
        polymarket_market_id=mid,
        polymarket_outcome_side=side,
        polymarket_stake_usd=stake,
        polymarket_question=question,
    )
