from __future__ import annotations

import time
from typing import Any

from apex.core.config import Settings
from apex.core.logging import get_logger
from apex.domain.models import AuditEvent, EventType

LOGGER = get_logger(__name__)

TRAILING_STOP_PCT_DEFAULT = 0.0  # 0 = disabled


def _loss_threshold(position: dict[str, Any], held_minutes: float) -> float:
    """Return the loss % that triggers an exit for this position.

    Tighter for equities (faster decay), looser for options (more noise).
    Scales down linearly over time so positions that linger get cut sooner.
    """
    is_option = position.get("asset_class") == "us_option"
    base = 30.0 if is_option else 4.0

    decay = min(2.0, held_minutes / 120.0)
    return round(base - decay, 1)


def _unrealized_pnl_pct(position: dict[str, Any]) -> float:
    """Return unrealized P&L as a signed percentage (negative = loss).

    Uses Alpaca's own ``unrealized_plpc`` when available, which is
    authoritative and avoids yfinance lookup failures for OCC symbols.
    """
    plpc = position.get("unrealized_plpc")
    if plpc is not None:
        try:
            return float(plpc) * 100.0
        except (TypeError, ValueError):
            pass
    return 0.0


def _peak_pnl(raw: dict[str, Any], current_pl_pct: float) -> float:
    """Return the highest P&L% seen so far for a position (trailing stop support)."""
    stored = raw.get("peak_pnl_pct")
    if stored is None:
        return current_pl_pct
    return max(float(stored), current_pl_pct)


def _daily_loss_exceeded(store: Any, settings: Settings) -> bool:
    """Check if cumulative daily loss exceeds ``daily_loss_limit_pct``.

    Queries completed trades from today and sums realized P&L.
    """
    limit = float(settings.daily_loss_limit_pct)
    if limit <= 0:
        return False
    try:
        trades_today = store.get_completed_trades(limit=500, days=1)
    except Exception:
        return False
    total_pl = sum(float(t.get("pnl", 0)) for t in trades_today if t.get("pnl"))
    account_equity = float(settings.initial_account_equity)
    try:
        from apex.integrations.hub import get_integration_hub
        hub = get_integration_hub()
        if hub.has_alpaca():
            raw = hub.alpaca_direct.get_account()
            account_equity = float(raw.get("equity", account_equity) or account_equity)
    except Exception:
        pass
    if account_equity <= 0:
        return False
    loss_pct = (total_pl / account_equity) * 100.0
    if loss_pct <= -limit:
        LOGGER.warning("Daily loss limit hit: %.1f%% (limit: %.1f%%)", loss_pct, -limit)
        return True
    return False


def _pm_position_pnl_pct(pm_pos: dict[str, Any], market_data: Any) -> float:
    """Compute a synthetic unrealized P&L% for a Polymarket paper position.

    Falls back to 0.0 when no market data is available (position is treated
    as within threshold and won't be cut).
    """
    entry = float(pm_pos.get("entry_price", 0))
    if entry <= 0:
        return 0.0
    sym = pm_pos["symbol"]
    try:
        current = float(market_data.get_intraday_price(sym) or 0)
    except Exception:
        return 0.0
    if current <= 0:
        return 0.0
    is_long = pm_pos.get("direction", "LONG") != "SHORT"
    if is_long:
        return ((current - entry) / entry) * 100.0
    return ((entry - current) / entry) * 100.0


def _pm_positions_from_store(store: Any) -> list[dict[str, Any]]:
    """Retrieve open Polymarket paper positions from the SQLite store."""
    getter = getattr(store, "get_pm_positions", None)
    if getter is None:
        return []
    return getter()


def loss_cut_scan(
    *,
    settings: Settings,
    broker: Any,
    store: Any,
    market_data: Any,
) -> list[str]:
    """Scan all open positions and close any that exceed the loss threshold.

    Returns symbols that were closed.
    """
    try:
        account = broker.get_account_snapshot()
    except Exception as exc:
        LOGGER.warning("loss_cut: cannot get account — %s", exc)
        return []

    # Check daily loss limit before scanning positions
    if _daily_loss_exceeded(store, settings):
        LOGGER.warning("loss_cut: daily loss limit exceeded — closing all positions")
        closed_all: list[str] = []
        for pos in account.open_positions:
            sym = pos.symbol
            closer = getattr(broker, "close_symbol_position", None)
            if closer and not sym.startswith("PM:"):
                try:
                    if closer(sym):
                        closed_all.append(sym)
                        store.append_event(
                            AuditEvent(
                                event_type=EventType.TRADE_CLOSED,
                                symbol=sym,
                                rejection_reason="daily_loss_limit",
                                raw_payload={"reason": "daily_loss_limit_exceeded"},
                            )
                        )
                except Exception as exc:
                    LOGGER.warning("loss_cut close failed for %s: %s", sym, exc)
        if closed_all:
            LOGGER.info("loss_cut closed %d positions via daily loss limit", len(closed_all))
        return closed_all

    closed: list[str] = []
    now_sec = time.time()
    trailing_pct = float(getattr(settings, "trailing_stop_pct", TRAILING_STOP_PCT_DEFAULT))

    for pos in account.open_positions:
        sym = pos.symbol
        if sym.startswith("PM:"):
            continue  # handled separately below

        raw = getattr(pos, "_raw", None) or pos.__dict__ if hasattr(pos, "__dict__") else {}
        held = (now_sec - raw.get("opened_at_epoch", now_sec)) / 60.0
        pl_pct = _unrealized_pnl_pct(raw)
        threshold = _loss_threshold(raw, held)

        # Trailing stop: lock in gains as price rises
        if trailing_pct > 0 and pl_pct > 0:
            peak = _peak_pnl(raw, pl_pct)
            drawdown = peak - pl_pct
            if drawdown >= trailing_pct:
                LOGGER.warning(
                    "loss_cut trailing stop %s (P&L=%.1f%% peak=%.1f%% drawdown=%.1f%% threshold=%.1f%%)",
                    sym, pl_pct, peak, drawdown, trailing_pct,
                )
                closer = getattr(broker, "close_symbol_position", None)
                if closer:
                    try:
                        if closer(sym):
                            closed.append(sym)
                            store.append_event(
                                AuditEvent(
                                    event_type=EventType.TRADE_CLOSED,
                                    symbol=sym,
                                    rejection_reason="trailing_stop",
                                    raw_payload={
                                        "pnl_pct": round(pl_pct, 2),
                                        "peak_pnl_pct": round(peak, 2),
                                        "drawdown_pct": round(drawdown, 2),
                                    },
                                )
                            )
                    except Exception as exc:
                        LOGGER.warning("loss_cut trailing stop failed for %s: %s", sym, exc)
                continue

        if pl_pct >= -threshold:
            continue

        LOGGER.warning(
            "loss_cut closing %s (P&L=%.1f%% threshold=%.1f%% held=%.0fmin)",
            sym, pl_pct, -threshold, held,
        )

        closer = getattr(broker, "close_symbol_position", None)
        if not closer:
            continue

        try:
            if closer(sym):
                closed.append(sym)
                store.append_event(
                    AuditEvent(
                        event_type=EventType.TRADE_CLOSED,
                        symbol=sym,
                        rejection_reason="loss_cut_brain",
                        raw_payload={
                            "pnl_pct": round(pl_pct, 2),
                            "threshold": -threshold,
                            "held_minutes": round(held, 0),
                        },
                    )
                )
        except Exception as exc:
            LOGGER.warning("loss_cut close failed for %s: %s", sym, exc)

    # Scan Polymarket paper positions (PM: prefix)
    try:
        pm_positions = _pm_positions_from_store(store)
        for pm_pos in pm_positions:
            sym = pm_pos["symbol"]
            pl_pct = _pm_position_pnl_pct(pm_pos, market_data)
            if pl_pct >= -4.0:  # PM positions get a flat 4% threshold
                continue
            LOGGER.warning(
                "loss_cut closing PM %s (P&L=%.1f%% threshold=%.1f%%)",
                sym, pl_pct, -4.0,
            )
            try:
                store.append_event(
                    AuditEvent(
                        event_type=EventType.TRADE_CLOSED,
                        symbol=sym,
                        rejection_reason="loss_cut_brain_pm",
                        raw_payload={"pnl_pct": round(pl_pct, 2), "threshold": 4.0},
                    )
                )
                closed.append(sym)
            except Exception as exc:
                LOGGER.warning("loss_cut PM close failed for %s: %s", sym, exc)
    except Exception as exc:
        LOGGER.debug("loss_cut: PM scan skipped — %s", exc)

    if closed:
        LOGGER.info("loss_cut closed %d positions: %s", len(closed), closed)

    return closed
