"""Arb scan + persist + L2 cache (Phase 2)."""

from __future__ import annotations

import os
import threading
import time
from typing import Any

from apex.core.config import Settings, get_settings
from apex.core.logging import get_logger
from apex.repositories.sqlite_store import SQLiteStore
from apex.services.arb_engine import ArbEngine
from apex.services.fast_cache import invalidate

LOGGER = get_logger(__name__)

_STAKE_FOR_VWAP = 50.0

# Single-flight + coalesce guard. The scheduler (~3 min), PM-agent loop (~5 min),
# and optional backend loop can all trigger full scans. Without this, two
# triggers that fire close together each run a complete (expensive) scan. The
# lock serializes scans; the coalesce window lets a second caller reuse a result
# that was just produced instead of re-scanning.
_SCAN_LOCK = threading.Lock()
# Keyed by db path so distinct stores (and tests) never share a cached result.
_SCAN_STATE: dict[str, dict[str, Any]] = {}
_SCAN_COALESCE_SEC = float(os.getenv("APEX_ARB_SCAN_COALESCE_SEC", "25"))


def _ingest_l2_for_opportunity(opp: Any, settings: Settings) -> float | None:
    """Cache orderbooks in Redis/memory; return executable vwap_edge if computable."""
    from apex.cache.orderbook_l2 import ingest_orderbook, read_orderbook
    from apex.execution.vwap import vwap_from_book
    from apex.integrations.kalshi_adapter import fetch_orderbook as fetch_kalshi_orderbook

    vwap_edge: float | None = None
    try:
        k_ob = fetch_kalshi_orderbook(opp.kalshi_ticker)
        ingest_orderbook("KALSHI", opp.kalshi_ticker, k_ob, redis_url=settings.redis_url)
        k_vwap, _ = vwap_from_book(k_ob, "yes", _STAKE_FOR_VWAP)
        if k_vwap is not None:
            gross = 1.0 - k_vwap - opp.poly_no_ask
            fee = 0.07 * (1.0 - k_vwap)
            vwap_edge = round(gross - fee, 4)
    except Exception as exc:
        LOGGER.debug("Kalshi L2 ingest skip %s: %s", opp.kalshi_ticker, exc)

    try:
        import requests

        resp = requests.get(
            f"https://clob.polymarket.com/book?token_id={opp.poly_market_id}",
            timeout=6,
        )
        if resp.ok:
            p_ob = resp.json()
            ingest_orderbook(
                "POLY",
                opp.poly_market_id,
                {"asks": p_ob.get("asks", []), "bids": p_ob.get("bids", [])},
                redis_url=settings.redis_url,
            )
            _ = read_orderbook("POLY", opp.poly_market_id, redis_url=settings.redis_url)
    except Exception as exc:
        LOGGER.debug("Poly L2 ingest skip %s: %s", opp.poly_market_id, exc)

    return vwap_edge


def scan_and_persist(
    store: SQLiteStore | None = None,
    *,
    settings: Settings | None = None,
    limit: int = 100,
    ingest_l2: bool = True,
    force: bool = False,
) -> list[Any]:
    """Run ArbEngine.scan and upsert into SQLite.

    Concurrent calls are serialized; a result produced within the coalesce
    window is reused instead of triggering a duplicate full scan (set
    ``force=True`` to bypass).
    """
    settings = settings or get_settings()
    store = store or SQLiteStore(settings.sqlite_path)
    key = str(settings.sqlite_path)

    from apex.observability import scan_metrics

    with _SCAN_LOCK:
        state = _SCAN_STATE.get(key)
        if not force and _SCAN_COALESCE_SEC > 0 and state:
            age = time.monotonic() - float(state["ts"])
            if (
                state["result"]
                and age < _SCAN_COALESCE_SEC
                and int(state["limit"]) >= limit
            ):
                scan_metrics.record_coalesce_hit()
                LOGGER.info(
                    "scan_and_persist: reusing scan from %.1fs ago (coalesced)", age
                )
                return list(state["result"])[:limit]

        _t0 = time.perf_counter()
        opps, engine = _run_scan_and_persist(
            store, settings=settings, limit=limit, ingest_l2=ingest_l2
        )
        total_ms = (time.perf_counter() - _t0) * 1000.0
        scan_metrics.record_scan(
            total_ms=total_ms,
            fetch_ms=getattr(engine, "_last_fetch_ms", 0.0),
            match_ms=getattr(engine, "_last_match_ms", 0.0),
            kalshi_count=getattr(engine, "_last_kalshi_count", 0),
            poly_count=getattr(engine, "_last_poly_count", 0),
            opportunities=len(opps),
        )
        _SCAN_STATE[key] = {
            "ts": time.monotonic(),
            "result": list(opps),
            "limit": limit,
        }
        return opps


def _run_scan_and_persist(
    store: SQLiteStore,
    *,
    settings: Settings,
    limit: int,
    ingest_l2: bool,
) -> tuple[list[Any], ArbEngine]:
    engine = ArbEngine(settings=settings, store=store)
    opps = engine.scan()[:limit]

    if not opps and settings.showcase_mode:
        from apex.demo.seed_data import seed_showcase_database

        seed_showcase_database(store)
        rows = store.list_arb_opportunities(limit=limit)
        if rows:
            from apex.domain.models import ArbOpportunity

            fields = ArbOpportunity.__dataclass_fields__
            opps = [
                ArbOpportunity(**{k: row[k] for k in fields if k in row})  # type: ignore[arg-type]
                for row in rows
            ]
            LOGGER.info("scan_and_persist: showcase fallback loaded %d opportunities", len(opps))

    try:
        from apex.observability.prometheus_metrics import APEX_ARB_EDGE

        if APEX_ARB_EDGE is not None and opps:
            APEX_ARB_EDGE.set(max(o.net_edge for o in opps))
    except Exception:
        pass

    if ingest_l2 and os.getenv("ARB_SCAN_INGEST_L2", "0").lower() in ("1", "true", "yes"):
        for opp in opps:
            ve = _ingest_l2_for_opportunity(opp, settings)
            if ve is not None:
                opp.vwap_edge = ve  # type: ignore[attr-defined]

    if opps:
        store.save_arb_opportunities(opps)
        if os.getenv("ARB_SCAN_WARM_L2", "0").lower() in ("1", "true", "yes"):
            from apex.cache.orderbook_l2 import ingest_orderbook
            from apex.integrations.kalshi_adapter import fetch_orderbook as fetch_k_ob

            for opp in opps[:10]:
                try:
                    k_ob = fetch_k_ob(opp.kalshi_ticker)
                    ingest_orderbook(
                        "KALSHI", opp.kalshi_ticker, k_ob, redis_url=settings.redis_url
                    )
                except Exception:
                    pass
    invalidate(f"pm_brain:{settings.sqlite_path}")
    LOGGER.info("scan_and_persist: saved %d opportunities", len(opps))
    return opps, engine
