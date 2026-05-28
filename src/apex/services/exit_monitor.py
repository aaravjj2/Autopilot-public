from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from apex.core.config import Settings
from apex.domain.enums import Direction
from apex.domain.models import OpportunityScore, Position


@dataclass(frozen=True)
class ExitDecision:
    reason: str


def _aware_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _move_pct(position: Position, price: float) -> float:
    entry = float(position.avg_entry_price)
    if entry <= 0:
        return -999.0
    is_long = position.side != "short"
    if is_long:
        return ((price - entry) / entry) * 100.0
    return ((entry - price) / entry) * 100.0


def _proposal_price_levels(
    proposal_targets: dict[str, Any] | None,
) -> tuple[float | None, float | None]:
    if not proposal_targets:
        return None, None
    stop = proposal_targets.get("stop_loss")
    take = proposal_targets.get("take_profit")
    try:
        stop_f = float(stop) if stop is not None else None
    except (TypeError, ValueError):
        stop_f = None
    try:
        take_f = float(take) if take is not None else None
    except (TypeError, ValueError):
        take_f = None
    return stop_f, take_f


def _hit_proposal_stop_tp(
    position: Position, price: float, stop: float | None, take: float | None
) -> ExitDecision | None:
    if stop is None and take is None:
        return None
    is_long = position.side != "short"
    if is_long:
        if stop is not None and price <= stop:
            return ExitDecision(reason="proposal_stop_loss")
        if take is not None and price >= take:
            return ExitDecision(reason="proposal_take_profit")
    else:
        if stop is not None and price >= stop:
            return ExitDecision(reason="proposal_stop_loss")
        if take is not None and price <= take:
            return ExitDecision(reason="proposal_take_profit")
    return None


def _vwap_from_bars(bars: list[dict[str, Any]]) -> float | None:
    """Calculate VWAP from a sorted list of OHLCV bars (most recent last)."""
    if not bars:
        return None
    pv_sum = 0.0
    vol_sum = 0.0
    for b in bars:
        try:
            typical = (float(b["high"]) + float(b["low"]) + float(b["close"])) / 3.0
            vol = float(b.get("volume", 0))
        except (KeyError, TypeError, ValueError):
            continue
        pv_sum += typical * vol
        vol_sum += vol
    if vol_sum <= 0:
        return None
    return pv_sum / vol_sum


def _multi_tf_exit_check(
    position: Position,
    price: float,
    bars_5min: list[dict[str, Any]] | None,
    bars_15min: list[dict[str, Any]] | None,
) -> ExitDecision | None:
    """Multi-timeframe exit check using VWAP and trend analysis.

    - If price is below VWAP on 15min bars → breakdown, suggest exit.
    - If price is above VWAP on 15min but below on 5min → hold (transient dip).
    - If both are above VWAP → healthy; return None.
    """
    vwap_15 = _vwap_from_bars(bars_15min) if bars_15min else None
    vwap_5 = _vwap_from_bars(bars_5min) if bars_5min else None
    if vwap_15 is None and vwap_5 is None:
        return None

    is_long = position.side != "short"

    # For long positions: price below 15min VWAP suggests breakdown
    if is_long:
        if vwap_15 is not None and price < vwap_15 * 0.995:
            return ExitDecision(reason="multi_tf_breakdown_15min")
        if vwap_5 is not None and price < vwap_5 * 0.99:
            return ExitDecision(reason="multi_tf_breakdown_5min")
    else:
        # Short positions: price above 15min VWAP suggests breakdown
        if vwap_15 is not None and price > vwap_15 * 1.005:
            return ExitDecision(reason="multi_tf_breakdown_15min")
        if vwap_5 is not None and price > vwap_5 * 1.01:
            return ExitDecision(reason="multi_tf_breakdown_5min")
    return None


def _hit_settings_stop_tp(
    position: Position, price: float, settings: Settings
) -> ExitDecision | None:
    move = _move_pct(position, price)
    if move <= -999:
        return ExitDecision(reason="invalid_entry_price")
    if move <= -abs(settings.exit_stop_pct):
        return ExitDecision(reason="stop_loss")
    if move >= abs(settings.exit_take_profit_pct):
        return ExitDecision(reason="take_profit")
    return None


def _max_hold_exceeded(entry_time: datetime, settings: Settings, now: datetime) -> bool:
    days = int(settings.exit_max_hold_days)
    if days <= 0:
        return False
    held = (_aware_utc(now) - _aware_utc(entry_time)).total_seconds() / 86400.0
    return held >= float(days)


def _signal_reversal(
    position: Position,
    opportunity: OpportunityScore | None,
    settings: Settings,
) -> bool:
    if not settings.exit_signal_reversal_enabled or opportunity is None:
        return False
    if opportunity.conviction < settings.conviction_floor:
        return False
    is_long = position.side != "short"
    if is_long and opportunity.direction == Direction.SHORT:
        return True
    if not is_long and opportunity.direction == Direction.LONG:
        return True
    return False


def evaluate_position_exit(
    *,
    position: Position,
    price: float,
    settings: Settings,
    opportunity: OpportunityScore | None,
    entry_time: datetime,
    proposal_targets: dict[str, Any] | None,
    eod_flatten: bool,
    now: datetime | None = None,
    bars_5min: list[dict[str, Any]] | None = None,
    bars_15min: list[dict[str, Any]] | None = None,
) -> ExitDecision | None:
    """Return an exit decision when the position should be closed, else None."""

    if eod_flatten and settings.exit_eod_flatten_enabled:
        return ExitDecision(reason="eod_flatten")

    if _max_hold_exceeded(entry_time, settings, now or datetime.now(tz=timezone.utc)):
        return ExitDecision(reason="max_hold_days")

    if _signal_reversal(position, opportunity, settings):
        return ExitDecision(reason="signal_reversal")

    # Multi-timeframe analysis: breakdown below VWAP triggers exit
    if settings.exit_use_proposal_stops:
        mtf = _multi_tf_exit_check(position, price, bars_5min, bars_15min)
        if mtf is not None:
            return mtf

    if settings.exit_use_proposal_stops:
        stop, take = _proposal_price_levels(proposal_targets)
        hit = _hit_proposal_stop_tp(position, price, stop, take)
        if hit is not None:
            return hit

    return _hit_settings_stop_tp(position, price, settings)
