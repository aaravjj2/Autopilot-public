"""FIFA World Cup 2026 discovery, scoring, and paper agent cycle."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from apex.core.config import get_settings
from apex.core.logging import get_logger
from apex.domain.enums import EventType
from apex.domain.models import AuditEvent, ArbOpportunity
from apex.integrations.world_cup_markets import discover_world_cup_markets, pair_cross_venue
from apex.ml.world_cup_model import apply_scores
from apex.repositories.sqlite_store import SQLiteStore
from apex.services.engine import ApexEngine
from apex.services.pm_trading import place_kalshi_paper_leg, place_polymarket_paper_leg
from apex.services.prediction_tiers import (
    bankroll_for_venue,
    build_prediction_signal,
)

LOGGER = get_logger(__name__)
_last_wc_cycle: dict[str, Any] = {}


def get_last_world_cup_cycle() -> dict[str, Any]:
    return dict(_last_wc_cycle)


def world_cup_status(store: SQLiteStore | None = None) -> dict[str, Any]:
    settings = get_settings()
    store = store or SQLiteStore(settings.sqlite_path)
    rows = store.list_world_cup_opportunities(limit=100)
    return {
        "enabled": settings.world_cup_enabled,
        "execution_mode": "paper_simulated",
        "opportunities_cached": len(rows),
        "last_cycle": get_last_world_cup_cycle(),
        "min_model_edge": settings.world_cup_min_model_edge,
        "use_poisson_model": bool(settings.world_cup_use_poisson),
        "confidence_tiers": "HIGH>=0.85, MID>=0.75, LOW=blocked",
        "simulation_endpoint": "/api/world-cup/simulation?n=1000",
    }


def discover_and_persist(store: SQLiteStore | None = None) -> list[dict[str, Any]]:
    settings = get_settings()
    store = store or SQLiteStore(settings.sqlite_path)
    raw = discover_world_cup_markets(settings)
    paired = pair_cross_venue(raw)
    scored = apply_scores(paired, settings)
    if scored:
        store.save_world_cup_opportunities(scored)
    return scored


def _wc_to_arb(row: dict[str, Any]) -> ArbOpportunity | None:
    kt = str(row.get("kalshi_ticker") or row.get("ticker_or_market_id") or "")
    pm = str(row.get("poly_market_id") or "")
    if not kt:
        return None
    if not pm:
        pm = f"wc-{row.get('id', 'unknown')}"
    return ArbOpportunity(
        id=str(row.get("pair_id") or row.get("id") or ""),
        kalshi_ticker=kt,
        poly_market_id=pm,
        question=str(row.get("question") or ""),
        kalshi_title=str(row.get("question") or ""),
        poly_title=str(row.get("question") or ""),
        kalshi_yes_ask=float(row.get("market_yes_ask") or row.get("kalshi_yes_ask") or 0.5),
        poly_no_ask=float(row.get("poly_no_ask") or (1.0 - float(row.get("market_yes_ask") or 0.5))),
        gross_spread=float(row.get("gross_spread") or 0),
        net_edge=float(row.get("net_edge") or 0),
        settlement_match_score=0.75,
        settlement_flags=[],
        volume_kalshi=float(row.get("volume_24h") or 0),
        volume_poly=float(row.get("volume_24h") or 0),
        category="WORLD_CUP",
        kelly_fraction=min(0.25, abs(float(row.get("model_edge") or 0)) * 5),
    )


async def run_world_cup_agent_cycle(engine: ApexEngine) -> dict[str, Any]:
    global _last_wc_cycle
    settings = engine.settings
    t0 = time.perf_counter()
    if not settings.world_cup_enabled:
        return {"status": "disabled", "detail": "WORLD_CUP_ENABLED=false"}

    scored = await asyncio.to_thread(discover_and_persist, engine.store)
    if not scored:
        scored = engine.store.list_world_cup_opportunities(limit=50)

    trades: list[dict[str, Any]] = []
    errors: list[str] = []
    cap = int(settings.world_cup_max_auto_trades_per_cycle)
    min_edge = float(settings.world_cup_min_model_edge)

    for row in scored[: cap * 3]:
        edge = float(row.get("model_edge") or 0)
        venue = row.get("venue")
        signal = build_prediction_signal(
            row,
            settings=settings,
            bankroll=bankroll_for_venue(settings, str(venue) if venue else None),
            min_edge=min_edge,
            kelly_cap=float(settings.kelly_alpha),
        )
        if signal is None:
            continue

        stake_usd = signal.suggested_stake_usd
        try:
            if venue == "kalshi" and row.get("kalshi_ticker"):
                r = await place_kalshi_paper_leg(
                    engine,
                    ticker=str(row["kalshi_ticker"]),
                    stake_usd=stake_usd,
                    price=float(row.get("market_yes_ask") or 0.5),
                    question=str(row.get("question") or ""),
                )
                if r.get("status") == "ok":
                    engine.store.append_event(
                        AuditEvent(
                            event_type=EventType.ORDER_FILLED,
                            symbol=str(row["kalshi_ticker"]),
                            order_id=r.get("order_id"),
                            raw_payload={
                                "venue": "kalshi_paper",
                                "world_cup": True,
                                "model_edge": edge,
                                "fair_prob": signal.fair_prob,
                                "confidence_tier": signal.tier.value,
                                "suggested_stake_usd": stake_usd,
                            },
                        )
                    )
                    trades.append(r)
            elif venue == "polymarket" and row.get("poly_market_id"):
                side = "YES" if edge > 0 else "NO"
                px = float(row.get("market_yes_ask") or 0.5)
                r = await place_polymarket_paper_leg(
                    engine,
                    market_id=str(row["poly_market_id"]),
                    outcome=side,
                    stake_usd=stake_usd,
                    price=px if side == "YES" else 1.0 - px,
                    question=str(row.get("question") or ""),
                )
                if r.get("status") == "ok":
                    engine.store.append_event(
                        AuditEvent(
                            event_type=EventType.ORDER_FILLED,
                            symbol=f"PM:{row['poly_market_id']}",
                            order_id=r.get("order_id"),
                            raw_payload={
                                "venue": "polymarket_paper",
                                "world_cup": True,
                                "model_edge": edge,
                                "confidence_tier": signal.tier.value,
                                "suggested_stake_usd": stake_usd,
                            },
                        )
                    )
                    trades.append(r)
            elif row.get("net_edge") and float(row.get("net_edge") or 0) >= settings.arb_min_net_edge:
                opp = _wc_to_arb(row)
                if opp:
                    risk = engine.execution.risk_engine.run_arb_paper(opp)
                    if risk.all_passed:
                        kid, pid = await engine.execution.submit_arb_paper_orders(opp)
                        if kid:
                            trades.append(
                                {"arb_id": opp.id, "kalshi_order_id": kid, "poly_order_id": pid}
                            )
                    else:
                        errors.append(f"{opp.id}:{risk.rejection_reason}")
        except Exception as exc:
            errors.append(str(exc))
        if len(trades) >= cap:
            break

    duration = round(time.perf_counter() - t0, 2)
    result = {
        "status": "ok",
        "discovery_count": len(scored),
        "paper_trade_count": len(trades),
        "trades": trades[:10],
        "errors": errors[:10],
        "duration_sec": duration,
        "execution_mode": "paper_simulated",
    }
    _last_wc_cycle = result
    engine.store.append_event(
        AuditEvent(
            event_type=EventType.SYSTEM_ALERT,
            raw_payload={"phase": "world_cup_agent_cycle", **result},
        )
    )
    return result
