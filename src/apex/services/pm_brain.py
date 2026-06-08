"""Prediction-market brain: Kalshi + Polymarket context for the dashboard."""

from __future__ import annotations

import time
from typing import Any

from apex.core.config import Settings, get_settings
from apex.repositories.sqlite_store import SQLiteStore
from apex.services.fast_cache import cached


def build_pm_brain(store: SQLiteStore | None = None, *, force: bool = False) -> dict[str, Any]:
    settings = get_settings()
    store = store or SQLiteStore(settings.sqlite_path)
    cache_key = f"pm_brain:{settings.sqlite_path}"

    if force:
        from apex.services.fast_cache import invalidate

        invalidate(cache_key)

    def _build() -> dict[str, Any]:
        return _build_pm_brain_uncached(store, settings)

    return cached(cache_key, ttl_sec=45.0, factory=_build)


def _build_pm_brain_uncached(store: SQLiteStore, settings: Settings) -> dict[str, Any]:
    now = time.time()
    rows = sorted(
        store.list_arb_opportunities(limit=25),
        key=lambda r: -(float(r.get("net_edge") or 0)),
    )
    opportunities = [
        {
            "id": r.get("id", ""),
            "question": r.get("question", ""),
            "kalshi_ticker": r.get("kalshi_ticker", ""),
            "net_edge": float(r.get("net_edge") or 0),
            "settlement_match_score": float(r.get("settlement_match_score") or 0),
        }
        for r in rows[:10]
    ]
    top_edge = max((float(r.get("net_edge") or 0) for r in rows), default=0.0)
    kalshi_status = "ok" if rows else "idle"
    poly_status = "ok" if rows else "idle"
    kalshi_detail = f"{len(rows)} cached pairs" if rows else "run arb scan to populate"
    poly_detail = kalshi_detail

    return {
        "timestamp": now,
        "paper_only": bool(settings.alpaca_paper_trade),
        "polymarket_paper_enabled": bool(settings.polymarket_paper_trading_enabled),
        "kalshi": {
            "status": kalshi_status,
            "detail": kalshi_detail,
            "min_volume_24h": settings.kalshi_min_volume_24h,
            "paper_bankroll_usd": settings.kalshi_paper_bankroll_usd,
        },
        "polymarket": {
            "status": poly_status,
            "detail": poly_detail,
            "paper_bankroll_usd": settings.polymarket_paper_bankroll_usd,
        },
        "arb": {
            "min_net_edge": settings.arb_min_net_edge,
            "relax_orderbook_checks": settings.arb_paper_relax_orderbook,
            "cached_opportunities": len(rows),
            "top_net_edge": top_edge,
            "fresh_scan_count": len(opportunities),
        },
        "recent_opportunities": opportunities,
        "guidance": (
            "Arb strategy: buy Kalshi YES + Polymarket NO when net_edge ≥ "
            f"{settings.arb_min_net_edge:.0%} after Kalshi 7% fee. "
            "All execution paths are paper-only."
        ),
        "world_cup": _world_cup_brain_block(store, settings),
    }


def _world_cup_brain_block(store: SQLiteStore, settings: Settings) -> dict[str, Any]:
    if not settings.world_cup_enabled:
        return {"status": "disabled", "enabled": False}
    try:
        wc = store.list_world_cup_opportunities(limit=15)
    except (KeyError, TypeError, AttributeError):
        wc = []
    top = wc[0] if wc else {}
    return {
        "enabled": True,
        "status": "ok" if wc else "idle",
        "cached_opportunities": len(wc),
        "top_model_edge": float(top.get("model_edge") or 0),
        "min_model_edge": settings.world_cup_min_model_edge,
    }
