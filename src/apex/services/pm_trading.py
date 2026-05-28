"""Kalshi & Polymarket paper trading helpers and unified PM agent automation."""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from apex.core.config import Settings, get_settings
from apex.core.logging import get_logger
from apex.domain.enums import EventType
from apex.domain.models import ArbOpportunity, AuditEvent
from apex.repositories.sqlite_store import SQLiteStore
from apex.services.engine import ApexEngine
from apex.integrations.kalshi_trading import kalshi_execution_mode_label, kalshi_execution_venue

LOGGER = get_logger(__name__)

_last_kalshi_cycle: dict[str, Any] = {}
_last_demo_probe_ts: float = 0.0


def get_last_kalshi_cycle() -> dict[str, Any]:
    return dict(_last_kalshi_cycle)


def _ensure_pm_brokers(settings: Settings) -> tuple[bool, str]:
    if not settings.alpaca_paper_trade:
        return False, "ALPACA_PAPER_TRADE must be true for Kalshi arb legs"
    if not settings.polymarket_paper_trading_enabled:
        return False, "POLYMARKET_PAPER_TRADING_ENABLED must be true"
    return True, ""


def arb_opportunity_from_row(row: dict[str, Any]) -> ArbOpportunity:
    """Build ArbOpportunity from SQLite normalized row."""
    flags = row.get("settlement_flags")
    if isinstance(flags, str):
        try:
            flags = json.loads(flags) if flags else []
        except json.JSONDecodeError:
            flags = []
    if not isinstance(flags, list):
        flags = list(flags or [])

    det_raw = row.get("detection_ts") or row.get("detected_at")
    if isinstance(det_raw, str) and det_raw:
        try:
            detection_ts = datetime.fromisoformat(det_raw.replace("Z", "+00:00"))
        except ValueError:
            detection_ts = datetime.now(timezone.utc)
    elif isinstance(det_raw, datetime):
        detection_ts = det_raw
    else:
        detection_ts = datetime.now(timezone.utc)

    return ArbOpportunity(
        id=str(row.get("id") or ""),
        kalshi_ticker=str(row.get("kalshi_ticker") or ""),
        poly_market_id=str(row.get("poly_market_id") or ""),
        question=str(row.get("question") or ""),
        kalshi_title=str(row.get("kalshi_title") or row.get("question") or ""),
        poly_title=str(row.get("poly_title") or row.get("question") or ""),
        kalshi_yes_ask=float(row.get("kalshi_yes_ask") or 0),
        poly_no_ask=float(row.get("poly_no_ask") or 0),
        gross_spread=float(row.get("gross_spread") or 0),
        net_edge=float(row.get("net_edge") or 0),
        settlement_match_score=float(row.get("settlement_match_score") or 0),
        settlement_flags=flags,
        detection_ts=detection_ts,
        volume_kalshi=float(row.get("volume_kalshi") or 0),
        volume_poly=float(row.get("volume_poly") or 0),
        category=str(row.get("category") or "UNKNOWN"),
        kelly_fraction=float(row.get("kelly_fraction") or 0),
        vwap_edge=float(row.get("vwap_edge") or 0),
    )


def load_cached_arb_opportunities(
    store: SQLiteStore,
    settings: Settings,
    *,
    limit: int = 50,
) -> list[ArbOpportunity]:
    """Active SQLite arbs above min edge, within max age."""
    max_age = timedelta(hours=float(settings.arb_cached_max_age_hours))
    cutoff = datetime.now(timezone.utc) - max_age
    opps: list[ArbOpportunity] = []
    for row in store.list_active_arb_opportunities(limit=limit):
        edge = float(row.get("net_edge") or 0)
        if edge < settings.arb_min_net_edge:
            continue
        det_raw = row.get("detection_ts") or row.get("detected_at")
        if det_raw:
            try:
                ts = datetime.fromisoformat(str(det_raw).replace("Z", "+00:00"))
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                if ts < cutoff:
                    continue
            except ValueError:
                pass
        if not row.get("kalshi_ticker") or not row.get("poly_market_id"):
            continue
        opps.append(arb_opportunity_from_row(row))
    return opps


async def place_kalshi_paper_leg(
    engine: ApexEngine,
    *,
    ticker: str,
    stake_usd: float,
    price: float,
    question: str = "",
) -> dict[str, Any]:
    """Single Kalshi YES leg via paper broker."""
    ok, msg = _ensure_pm_brokers(engine.settings)
    if not ok:
        return {"status": "error", "detail": msg}
    broker = engine.execution.broker
    submit = getattr(broker, "submit_kalshi_paper", None)
    if not callable(submit):
        return {"status": "error", "detail": "Kalshi paper broker not configured"}
    try:
        order_id = await submit(ticker=ticker, stake_usd=stake_usd, price=price)
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}
    venue = "kalshi_paper"
    engine.store.append_event(
        AuditEvent(
            event_type=EventType.ORDER_FILLED,
            symbol=ticker,
            order_id=order_id,
            raw_payload={
                "venue": venue,
                "kalshi_ticker": ticker,
                "stake_usd": stake_usd,
                "entry_price": price,
                "kalshi_yes_ask": price,
                "question": question or ticker,
                "kalshi_demo": engine.settings.kalshi_demo_trading_enabled,
            },
        )
    )
    return {"status": "ok", "order_id": order_id, "venue": venue}


async def place_polymarket_paper_leg(
    engine: ApexEngine,
    *,
    market_id: str,
    outcome: str,
    stake_usd: float,
    price: float,
    question: str = "",
) -> dict[str, Any]:
    """Single Polymarket leg via paper broker."""
    ok, msg = _ensure_pm_brokers(engine.settings)
    if not ok:
        return {"status": "error", "detail": msg}
    broker = engine.execution.broker
    submit = getattr(broker, "submit_polymarket_paper", None)
    if not callable(submit):
        return {"status": "error", "detail": "Polymarket paper broker not configured"}
    try:
        order_id = await submit(
            market_id=market_id,
            outcome=outcome.upper(),
            stake_usd=stake_usd,
            price=price,
        )
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}
    engine.store.append_event(
        AuditEvent(
            event_type=EventType.ORDER_FILLED,
            symbol=f"PM:{market_id}",
            order_id=order_id,
            raw_payload={
                "venue": "polymarket_paper",
                "polymarket_market_id": market_id,
                "polymarket_outcome_side": outcome.upper(),
                "polymarket_stake_usd": stake_usd,
                "polymarket_question": question or market_id,
                "entry_price": price,
            },
        )
    )
    return {"status": "ok", "order_id": order_id, "venue": "polymarket_paper"}


def run_polymarket_agent_cycle(engine: ApexEngine) -> dict[str, Any]:
    """Discovery agent + paper submission agent (scheduler job equivalent)."""
    settings = engine.settings
    if not settings.polymarket_paper_trading_enabled:
        return {"status": "disabled", "detail": "POLYMARKET_PAPER_TRADING_ENABLED=false"}
    try:
        proposals = engine.polymarket_event_discovery()
    except Exception as exc:
        LOGGER.warning("run_polymarket_agent_cycle: discovery failed: %s", exc)
        return {
            "status": "error",
            "discovery_count": 0,
            "submitted_count": 0,
            "order_ids": [],
            "detail": f"discovery_failed: {exc}",
        }
    if not settings.polymarket_automated_events_enabled:
        return {
            "status": "ok",
            "discovery_count": len(proposals),
            "submitted_count": 0,
            "order_ids": [],
            "detail": "automated submission off; proposals discovered only",
        }
    try:
        order_ids = engine.polymarket_paper_order_submission(proposals)
    except Exception as exc:
        LOGGER.warning("run_polymarket_agent_cycle: submission failed: %s", exc)
        return {
            "status": "error",
            "discovery_count": len(proposals),
            "submitted_count": 0,
            "order_ids": [],
            "detail": f"submission_failed: {exc}",
        }
    return {
        "status": "ok",
        "discovery_count": len(proposals),
        "submitted_count": len(order_ids),
        "order_ids": order_ids[:20],
    }


async def maybe_kalshi_demo_probe_trade(
    engine: ApexEngine,
    settings: Settings,
) -> dict[str, Any] | None:
    """
    When demo trading is on but no arb legs qualify, place one small YES order
    on a liquid demo-market so the Kalshi demo portfolio shows activity.
    """
    global _last_demo_probe_ts
    if not settings.kalshi_demo_trading_enabled or not settings.kalshi_demo_probe_enabled:
        return None
    interval = int(settings.kalshi_demo_probe_interval_sec)
    if time.time() - _last_demo_probe_ts < interval:
        return None
    from apex.integrations.kalshi_adapter import KalshiEventClient
    from apex.integrations.kalshi_demo_broker import KalshiDemoBroker
    from apex.integrations.kalshi_trading import kalshi_credentials_configured

    if not kalshi_credentials_configured(settings):
        return None

    broker = engine.execution.broker
    kalshi_broker = getattr(broker, "kalshi_paper", None)
    if not isinstance(kalshi_broker, KalshiDemoBroker):
        return None

    client = KalshiEventClient(settings)
    markets = await asyncio.to_thread(client.get_macro_markets, min_volume=0, fast=True)
    pick = None
    for m in markets:
        if 0.08 < m.best_ask_yes < 0.92:
            pick = m
            break
    if pick is None and markets:
        pick = markets[0]
    if pick is None:
        return None

    stake = float(settings.kalshi_demo_probe_stake_usd)
    price = max(0.09, min(0.91, float(pick.best_ask_yes)))

    def _submit() -> dict[str, Any]:
        order_id = kalshi_broker.submit_yes_leg(pick.ticker, stake, price)
        filled, detail = kalshi_broker.monitor_fill(order_id, timeout_seconds=45)
        return {
            "status": "ok" if filled else "submitted",
            "order_id": order_id,
            "ticker": pick.ticker,
            "stake_usd": stake,
            "price": price,
            "fill_detail": detail,
            "probe": True,
        }

    try:
        result = await asyncio.to_thread(_submit)
        _last_demo_probe_ts = time.time()
        engine.store.append_event(
            AuditEvent(
                event_type=EventType.SYSTEM_ALERT,
                symbol=f"KALSHI:{pick.ticker}",
                raw_payload={"phase": "kalshi_demo_probe", **result},
            )
        )
        return result
    except Exception as exc:
        LOGGER.warning("Kalshi demo probe order failed: %s", exc)
        return {"status": "error", "detail": str(exc), "ticker": pick.ticker, "probe": True}


def _is_seeded_demo_opportunity(opp: ArbOpportunity) -> bool:
    """Hackathon/demo SQLite rows — not valid on Kalshi demo exchange."""
    oid = str(getattr(opp, "id", "") or "")
    poly = str(getattr(opp, "poly_market_id", "") or "")
    return oid.startswith("demo-") or poly.startswith("0xdemo-")


async def _paper_trade_opportunities(
    engine: ApexEngine,
    opps: list[ArbOpportunity],
    settings: Settings,
) -> tuple[list[dict[str, Any]], list[str]]:
    trades: list[dict[str, Any]] = []
    errors: list[str] = []
    ranked = sorted(opps, key=lambda o: -(float(getattr(o, "net_edge", 0) or 0)))
    cap = int(settings.kalshi_arb_max_auto_trades_per_cycle)
    for opp in ranked[:cap]:
        if settings.kalshi_demo_trading_enabled and _is_seeded_demo_opportunity(opp):
            continue
        edge = float(getattr(opp, "net_edge", 0) or 0)
        if edge < settings.arb_min_net_edge:
            continue
        risk = engine.execution.risk_engine.run_arb_paper(opp)
        if not risk.all_passed:
            errors.append(f"{opp.id}:{risk.rejection_reason}")
            continue
        try:
            kid, pid = await engine.execution.submit_arb_paper_orders(opp, thesis=None)
        except Exception as exc:
            errors.append(f"{opp.id}:{exc}")
            continue
        if kid:
            trades.append(
                {
                    "arb_id": opp.id,
                    "kalshi_order_id": kid,
                    "poly_order_id": pid,
                    "net_edge": edge,
                }
            )
    return trades, errors


async def run_kalshi_arb_agent_cycle(
    engine: ApexEngine,
    *,
    auto_paper: bool | None = None,
    fast_scan: bool | None = None,
) -> dict[str, Any]:
    """Scan Kalshi↔Poly arb opportunities and optionally paper-trade top edges."""
    global _last_kalshi_cycle
    from apex.integrations.kalshi_adapter import get_last_kalshi_scan_metrics
    from apex.services.arb_scan import scan_and_persist

    settings = engine.settings
    t0 = time.perf_counter()
    if not settings.pm_agents_automation_enabled:
        return {"status": "disabled", "detail": "PM_AGENTS_AUTOMATION_ENABLED=false"}

    ok, msg = _ensure_pm_brokers(settings)
    if not ok:
        return {"status": "error", "detail": msg}

    use_fast = settings.pm_agent_fast_scan if fast_scan is None else fast_scan
    cached_used = False
    opps: list[Any] = []

    if use_fast and settings.kalshi_agent_use_cached_opps:
        cached = load_cached_arb_opportunities(engine.store, settings, limit=50)
        if cached:
            if settings.kalshi_demo_trading_enabled:
                cached = [o for o in cached if not _is_seeded_demo_opportunity(o)]
            if cached:
                opps = cached
                cached_used = True

    if not opps:
        opps = await asyncio.to_thread(
            scan_and_persist,
            engine.store,
            settings=settings,
            limit=50,
            ingest_l2=False,
        )
        if not opps and settings.kalshi_agent_use_cached_opps:
            cached = load_cached_arb_opportunities(engine.store, settings, limit=50)
            if cached:
                opps = cached
                cached_used = True

    duration_sec = round(time.perf_counter() - t0, 2)
    engine.store.append_event(
        AuditEvent(
            event_type=EventType.SYSTEM_ALERT,
            raw_payload={
                "phase": "kalshi_arb_agent_cycle",
                "venue": "kalshi_paper",
                "scan_count": len(opps),
                "cached_used": cached_used,
                "fast_scan": use_fast,
                "kalshi_scan_metrics": get_last_kalshi_scan_metrics(),
            },
        )
    )

    do_paper = (
        auto_paper
        if auto_paper is not None
        else settings.kalshi_arb_automated_paper_enabled
    )
    trades: list[dict[str, Any]] = []
    errors: list[str] = []

    if do_paper and opps:
        trades, errors = await _paper_trade_opportunities(engine, opps, settings)

    demo_probe: dict[str, Any] | None = None
    if settings.kalshi_demo_trading_enabled and not trades:
        demo_probe = await maybe_kalshi_demo_probe_trade(engine, settings)
        if demo_probe and demo_probe.get("order_id"):
            trades.append(
                {
                    "arb_id": "demo-probe",
                    "kalshi_order_id": demo_probe["order_id"],
                    "poly_order_id": None,
                    "net_edge": 0.0,
                    "probe": True,
                }
            )

    result = {
        "status": "ok",
        "scan_count": len(opps),
        "cached_used": cached_used,
        "fast_scan": use_fast,
        "paper_trades": trades,
        "paper_trade_count": len(trades),
        "demo_probe": demo_probe,
        "errors": errors[:10],
        "auto_paper": do_paper,
        "duration_sec": duration_sec,
        "kalshi_scan_metrics": get_last_kalshi_scan_metrics(),
    }
    _last_kalshi_cycle = result
    return result


async def run_prediction_markets_agent_cycle(
    engine: ApexEngine,
    *,
    fast_scan: bool | None = None,
) -> dict[str, Any]:
    """Run Polymarket event agent + Kalshi arb agent in one automated pass."""
    settings = engine.settings
    if not settings.pm_agents_automation_enabled:
        return {"status": "disabled", "detail": "PM_AGENTS_AUTOMATION_ENABLED=false"}

    ok, msg = _ensure_pm_brokers(settings)
    if not ok:
        return {"status": "error", "detail": msg}

    poly = await asyncio.to_thread(run_polymarket_agent_cycle, engine)
    kalshi = await run_kalshi_arb_agent_cycle(engine, fast_scan=fast_scan)

    engine.store.append_event(
        AuditEvent(
            event_type=EventType.SYSTEM_ALERT,
            raw_payload={
                "phase": "prediction_markets_agent_cycle",
                "polymarket": poly,
                "kalshi_arb": kalshi,
            },
        )
    )

    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "execution_mode": kalshi_execution_mode_label(engine.settings),
        "polymarket": poly,
        "kalshi_arb": kalshi,
    }


def pm_agents_status(engine: ApexEngine, store: SQLiteStore | None = None) -> dict[str, Any]:
    """Runtime status for Kalshi/Polymarket paper agents."""
    from apex.integrations.kalshi_adapter import get_last_kalshi_scan_metrics
    from apex.services.pm_brain import build_pm_brain
    from apex.services.prediction_books import build_kalshi_book, build_polymarket_book

    store = store or engine.store
    settings = engine.settings
    broker = engine.execution.broker
    kalshi_broker = getattr(broker, "kalshi_paper", None)
    poly_broker = getattr(broker, "polymarket_paper", None)
    kalshi_ok = kalshi_broker is not None
    poly_ok = poly_broker is not None
    kalshi_demo = settings.kalshi_demo_trading_enabled and kalshi_broker is not None
    mode = kalshi_execution_mode_label(settings)
    kalshi_book = build_kalshi_book(store)
    polymarket_book = build_polymarket_book(store)
    return {
        "execution_mode": mode,
        "kalshi_demo_trading_enabled": settings.kalshi_demo_trading_enabled,
        "kalshi_demo_broker": kalshi_demo,
        "kalshi_base_url": settings.kalshi_base_url,
        "kalshi_paper_broker": kalshi_ok,
        "polymarket_paper_broker": poly_ok,
        "alpaca_paper_trade": settings.alpaca_paper_trade,
        "polymarket_paper_enabled": settings.polymarket_paper_trading_enabled,
        "polymarket_automated_events": settings.polymarket_automated_events_enabled,
        "pm_agents_automation_enabled": settings.pm_agents_automation_enabled,
        "kalshi_arb_automated_paper": settings.kalshi_arb_automated_paper_enabled,
        "kalshi_agent_use_cached_opps": settings.kalshi_agent_use_cached_opps,
        "pm_agent_fast_scan": settings.pm_agent_fast_scan,
        "pm_agent_loop_interval_sec": settings.pm_agent_loop_interval_sec,
        "last_kalshi_cycle": get_last_kalshi_cycle(),
        "kalshi_scan_metrics": get_last_kalshi_scan_metrics(),
        "brain": build_pm_brain(store),
        "kalshi_book": {
            "open_positions": kalshi_book["open_positions"],
            "trades": len(kalshi_book["trades"]),
            "execution_mode": mode,
        },
        "polymarket_book": {
            "open_positions": polymarket_book["summary"]["open_positions"],
            "trades": len(polymarket_book["trades"]),
            "execution_mode": "paper_simulated",
        },
    }
