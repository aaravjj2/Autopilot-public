"""APEX Trading Terminal Backend API - Real Engine Integration with Alpaca"""
from __future__ import annotations

import os
import sys
import json
import logging
import asyncio
import subprocess
import math
import re
import requests
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from datetime import datetime, timezone
from typing import Any
from collections import deque
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from apex.core.env_bootstrap import bootstrap_environment

bootstrap_environment(force=True)

from contextlib import asynccontextmanager  # noqa: E402

from fastapi import Body, FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect  # noqa: E402
from fastapi.responses import StreamingResponse  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from apex.core.config import get_settings  # noqa: E402
from apex.repositories.sqlite_store import SQLiteStore  # noqa: E402
from apex.services.thesis_client import ThesisClient  # noqa: E402
from apex.integrations.brightdata_intelligence import BrightDataIntelligence  # noqa: E402
from apex.agents.arb_intelligence_agent import ArbitrageIntelligenceAgent  # noqa: E402

# Initialize real engine components
settings = get_settings()
store = SQLiteStore(settings.sqlite_path)
thesis_client = ThesisClient()
logger = logging.getLogger(__name__)

# Use existing Alpaca adapter instead of duplicating logic
from apex.integrations.market_facade import get_alpaca_client, get_chart_bars, get_options_chain, probe_market_feeds, record_equity_snapshot  # noqa: E402

def _alpaca():
    return get_alpaca_client(settings)


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        dead = []
        for conn in self.active_connections:
            try:
                await conn.send_json(message)
            except Exception:
                dead.append(conn)
        for conn in dead:
            self.disconnect(conn)

manager = ConnectionManager()
_INTEL_REPORT_DIR = Path("data/intelligence_reports").resolve()
_INTEL_REPORT_DIR.mkdir(parents=True, exist_ok=True)
_INTEL_TICKER_RE = re.compile(r"^[A-Za-z0-9._-]+$")
_INTEL_IN_FLIGHT: set[str] = set()
_INTEL_SEMAPHORE = asyncio.Semaphore(2)
_INTEL_IN_FLIGHT_LOCK = asyncio.Lock()

# Cache with freshness tracking
_ALPACA_POOL = ThreadPoolExecutor(max_workers=4, thread_name_prefix="apex-alpaca")


class DataCache:
    def __init__(self):
        self._positions = []
        self._orders = []
        self._order_history = []
        self._account = {}
        self._opportunities = []
        self._proposals = []
        self._events = deque(maxlen=200)
        self._last_update = None
        self._data_age_seconds = 0
        self._is_stale = False
        self._alpaca_connected = False
        self._revision = 0
        self._thread_lock = threading.Lock()

    def _refresh_alpaca_parallel(self) -> None:
        alpaca = _alpaca()
        if not alpaca.available:
            self._is_stale = True
            self._alpaca_connected = False
            self._account = {"error": "Alpaca not configured"}
            self._positions = []
            self._orders = []
            self._order_history = []
            return

        f_account = _ALPACA_POOL.submit(alpaca.get_account)
        f_positions = _ALPACA_POOL.submit(alpaca.get_positions)
        f_orders = _ALPACA_POOL.submit(alpaca.get_orders, "open")
        f_history = _ALPACA_POOL.submit(alpaca.get_order_history, 50)
        for fut in as_completed(
            (f_account, f_positions, f_orders, f_history), timeout=12
        ):
            fut.result()
        self._account = f_account.result()
        self._positions = f_positions.result()
        self._orders = f_orders.result()
        self._order_history = f_history.result()
        self._is_stale = False
        self._alpaca_connected = True
        try:
            from apex.observability.prometheus_metrics import APEX_POSITIONS

            if APEX_POSITIONS is not None:
                APEX_POSITIONS.set(len(self._positions))
        except Exception:
            pass

    def _hydrate_audit_once(self, limit: int = 100) -> None:
        opportunities: list[dict] = []
        proposals: list[dict] = []
        events: list[dict] = []
        try:
            rows = store.read_table("audit_log", limit=limit)
        except Exception:
            self._opportunities = []
            self._proposals = []
            self._events = deque(maxlen=200)
            return

        for event in rows:
            et = event.get("event_type", "")
            payload = event.get("raw_payload", {})
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except Exception:
                    payload = {}

            if et == "OPPORTUNITY_SCORED":
                opportunities.append({
                    "symbol": event.get("symbol", ""),
                    "direction": payload.get("direction", "NEUTRAL"),
                    "instrument": payload.get("instrument", "EQUITY"),
                    "conviction": float(payload.get("conviction", 0)),
                    "technical_score": float(payload.get("technical_score", 0)),
                    "fundamental_score": float(payload.get("fundamental_score", 0)),
                    "pm_signal": payload.get("pm_signal", "NEUTRAL"),
                    "catalyst": payload.get("catalyst", ""),
                    "risk_reward": float(payload.get("risk_reward", 0)),
                })
            elif et == "PROPOSAL_CREATED":
                proposals.append({
                    "id": event.get("event_id", ""),
                    "symbol": event.get("symbol", ""),
                    "direction": payload.get("direction", "LONG"),
                    "instrument": payload.get("instrument", "EQUITY"),
                    "entry_price": float(payload.get("entry_price", 0)),
                    "stop_loss": float(payload.get("stop_loss", 0)),
                    "take_profit": float(payload.get("take_profit", 0)),
                    "conviction": float(payload.get("conviction_final", 0)),
                    "status": "EXECUTED",
                    "created_at": event.get("timestamp", datetime.now(timezone.utc).isoformat()),
                })

            events.append({
                "id": event.get("event_id", ""),
                "event_type": et,
                "symbol": event.get("symbol"),
                "conviction": event.get("conviction"),
                "rejection_reason": event.get("rejection_reason"),
                "order_id": event.get("order_id"),
                "timestamp": event.get("timestamp", datetime.now(timezone.utc).isoformat()),
                "raw_payload": payload,
            })

        self._opportunities = opportunities
        self._proposals = proposals
        self._events = deque(events, maxlen=200)

    def refresh(self):
        with self._thread_lock:
            self._refresh_locked()

    def _refresh_locked(self):
        try:
            self._refresh_alpaca_parallel()
            self._hydrate_audit_once()
            if self._alpaca_connected:
                try:
                    record_equity_snapshot(store, self._account)
                except Exception as exc:
                    print(f"equity snapshot error: {exc}")
            self._last_update = datetime.now(timezone.utc).isoformat()
            self._data_age_seconds = 0
            self._revision += 1
        except Exception as e:
            print(f"Cache refresh error: {e}")
            self._is_stale = True
    
    def mark_stale_if_needed(self):
        if self._last_update:
            last = datetime.fromisoformat(self._last_update)
            age = (datetime.now(timezone.utc) - last).total_seconds()
            self._data_age_seconds = age
            if self._alpaca_connected:
                self._is_stale = age > 300  # 5 minutes stale threshold
    
    def _get_opportunities(self) -> list[dict]:
        try:
            events = store.read_table("audit_log", limit=50)
            opportunities = []
            for event in events:
                if event.get("event_type") == "OPPORTUNITY_SCORED":
                    payload = event.get("raw_payload", {})
                    if isinstance(payload, str):
                        payload = json.loads(payload)
                    opportunities.append({
                        "symbol": event.get("symbol", ""),
                        "direction": payload.get("direction", "NEUTRAL"),
                        "instrument": payload.get("instrument", "EQUITY"),
                        "conviction": float(payload.get("conviction", 0)),
                        "technical_score": float(payload.get("technical_score", 0)),
                        "fundamental_score": float(payload.get("fundamental_score", 0)),
                        "pm_signal": payload.get("pm_signal", "NEUTRAL"),
                        "catalyst": payload.get("catalyst", ""),
                        "risk_reward": float(payload.get("risk_reward", 0)),
                    })
            if opportunities:
                return opportunities
        except Exception:
            return []
    
    def _get_proposals(self) -> list[dict]:
        try:
            events = store.read_table("audit_log", limit=50)
            proposals = []
            for event in events:
                if event.get("event_type") == "PROPOSAL_CREATED":
                    payload = event.get("raw_payload", {})
                    if isinstance(payload, str):
                        payload = json.loads(payload)
                    proposals.append({
                        "id": event.get("event_id", ""),
                        "symbol": event.get("symbol", ""),
                        "direction": payload.get("direction", "LONG"),
                        "instrument": payload.get("instrument", "EQUITY"),
                        "entry_price": float(payload.get("entry_price", 0)),
                        "stop_loss": float(payload.get("stop_loss", 0)),
                        "take_profit": float(payload.get("take_profit", 0)),
                        "conviction": float(payload.get("conviction_final", 0)),
                        "status": "EXECUTED",
                        "created_at": event.get("timestamp", datetime.now(timezone.utc).isoformat()),
                    })
            return proposals
        except Exception:
            return []
    
    def _get_events(self, limit: int = 100) -> list[dict]:
        try:
            events = store.read_table("audit_log", limit=limit)
            result = []
            for event in events:
                payload = event.get("raw_payload", {})
                if isinstance(payload, str):
                    try:
                        payload = json.loads(payload)
                    except json.JSONDecodeError:
                        logger.debug("Failed to parse event payload as JSON, using empty dict")
                        payload = {}
                result.append({
                    "id": event.get("event_id", ""),
                    "event_type": event.get("event_type", ""),
                    "symbol": event.get("symbol"),
                    "conviction": event.get("conviction"),
                    "rejection_reason": event.get("rejection_reason"),
                    "order_id": event.get("order_id"),
                    "timestamp": event.get("timestamp", datetime.now(timezone.utc).isoformat()),
                    "raw_payload": payload,
                })
            if result:
                return result
        except Exception:
            return []

cache = DataCache()


def _sse_event(event: str, payload: dict | str) -> str:
    data = payload if isinstance(payload, str) else json.dumps(payload)
    return f"event: {event}\ndata: {data}\n\n"

def _ws_payload() -> dict:
    cache.mark_stale_if_needed()
    return {
        "type": "snapshot",
        "account": _normalize_account(cache._account or {}),
        "positions": _normalize_positions(cache._positions),
        "orders": cache._orders,
        "opportunities": cache._opportunities,
        "proposals": cache._proposals,
        "events": list(cache._events),
        "_is_stale": cache._is_stale,
        "_data_age_seconds": cache._data_age_seconds,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


_REFRESH_SEC = float(os.getenv("APEX_CACHE_REFRESH_SEC", "12"))
_WS_TICK_SEC = float(os.getenv("APEX_WS_TICK_SEC", "4"))
_last_ws_fp: str | None = None


def _ws_fingerprint(payload: dict) -> str:
    acc = payload.get("account") or {}
    return (
        f"{cache._revision}:{acc.get('equity')}:{len(payload.get('positions') or [])}:"
        f"{len(payload.get('opportunities') or [])}:{len(payload.get('events') or [])}"
    )


async def data_refresh_loop():
    """Pull Alpaca + SQLite on a slower cadence."""
    while True:
        try:
            await asyncio.wait_for(asyncio.to_thread(cache.refresh), timeout=20.0)
        except Exception as exc:
            print(f"data_refresh_loop error: {exc}")
        await asyncio.sleep(_REFRESH_SEC)


_arb_scan_seq = 0
_pm_agents_seq = 0
_equity_autopilot_seq = 0
_self_improvement_seq = 0


async def pm_agents_loop():
    """Background Polymarket + Kalshi arb paper agents."""
    from apex.services.pm_trading import run_prediction_markets_agent_cycle

    global _pm_agents_seq
    interval = float(
        os.getenv("PM_AGENT_LOOP_INTERVAL_SEC", str(get_settings().pm_agent_loop_interval_sec))
    )
    cycle_timeout = float(os.getenv("PM_AGENT_CYCLE_TIMEOUT_SEC", "120"))
    while True:
        try:
            engine = get_cached_engine()
            result = await asyncio.wait_for(
                run_prediction_markets_agent_cycle(engine),
                timeout=cycle_timeout,
            )
            _pm_agents_seq += 1
            await manager.broadcast({
                "type": "pm_agents_complete",
                "seq": _pm_agents_seq,
                "result": result,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        except asyncio.TimeoutError:
            print("pm_agents_loop: cycle timed out")
        except Exception as exc:
            print(f"pm_agents_loop error: {exc}")
        await asyncio.sleep(interval)


async def equity_autopilot_loop():
    """Intraday Alpaca: score watchlist, run agent panel, submit paper orders."""
    global _equity_autopilot_seq
    s = get_settings()
    interval = float(
        os.getenv("EQUITY_LOOP_INTERVAL_SEC", str(s.equity_loop_interval_sec))
    )
    cycle_timeout = float(os.getenv("EQUITY_CYCLE_TIMEOUT_SEC", "600"))
    while True:
        try:
            if not s.equity_autopilot_enabled or os.getenv(
                "APEX_EQUITY_LOOP", "true"
            ).lower() not in ("1", "true", "yes"):
                await asyncio.sleep(interval)
                continue
            engine = get_cached_engine()
            result = await asyncio.wait_for(
                asyncio.to_thread(engine.equity_autopilot_cycle),
                timeout=cycle_timeout,
            )
            _equity_autopilot_seq += 1
            await manager.broadcast({
                "type": "equity_autopilot_complete",
                "seq": _equity_autopilot_seq,
                "result": result,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        except asyncio.TimeoutError:
            print("equity_autopilot_loop: cycle timed out")
        except Exception as exc:
            print(f"equity_autopilot_loop error: {exc}")
        await asyncio.sleep(interval)


async def self_improvement_loop():
    """Daily export → train → evaluate → promote when enabled."""
    from apex.services.self_improvement import run_self_improvement_cycle

    global _self_improvement_seq
    interval = float(
        os.getenv(
            "SELF_IMPROVEMENT_LOOP_INTERVAL_SEC",
            str(get_settings().self_improvement_loop_interval_sec),
        )
    )
    cycle_timeout = float(os.getenv("SELF_IMPROVEMENT_CYCLE_TIMEOUT_SEC", "180"))
    while True:
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(run_self_improvement_cycle, get_cached_engine()),
                timeout=cycle_timeout,
            )
            _self_improvement_seq += 1
            await manager.broadcast({
                "type": "self_improvement_complete",
                "seq": _self_improvement_seq,
                "result": result,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        except asyncio.TimeoutError:
            print("self_improvement_loop: cycle timed out")
        except Exception as exc:
            print(f"self_improvement_loop error: {exc}")
        await asyncio.sleep(interval)


async def arb_scan_loop():
    """Background Kalshi/Poly scan when scheduler container is not running."""
    from apex.services.arb_scan import scan_and_persist

    global _arb_scan_seq
    os.environ.setdefault("ARB_SCAN_INGEST_L2", "1")
    os.environ.setdefault("ARB_SCAN_WARM_L2", "1")
    interval = float(os.getenv("ARB_SCAN_INTERVAL_SEC", str(get_settings().arb_scan_interval_sec)))
    scan_timeout = float(os.getenv("ARB_SCAN_TIMEOUT_SEC", "90"))
    while True:
        try:
            await asyncio.wait_for(
                asyncio.to_thread(
                    scan_and_persist,
                    store,
                    limit=50,
                    ingest_l2=True,
                ),
                timeout=scan_timeout,
            )
            _arb_scan_seq += 1
            await manager.broadcast({
                "type": "arb_scan_complete",
                "seq": _arb_scan_seq,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        except asyncio.TimeoutError:
            print("arb_scan_loop: scan timed out (API stays responsive)")
        except Exception as exc:
            print(f"arb_scan_loop error: {exc}")
        await asyncio.sleep(interval)


async def ws_broadcast_loop():
    """Push WS updates from cache without re-fetching Alpaca."""
    global _last_ws_fp
    while True:
        try:
            payload = _ws_payload()
            fp = _ws_fingerprint(payload)
            if fp != _last_ws_fp:
                _last_ws_fp = fp
                await manager.broadcast(payload)
            elif manager.active_connections:
                await manager.broadcast({
                    "type": "heartbeat",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "_data_age_seconds": cache._data_age_seconds,
                })
        except Exception as exc:
            print(f"ws_broadcast_loop error: {exc}")
        await asyncio.sleep(_WS_TICK_SEC)


_engine_singleton: Any = None


def get_cached_engine():
    global _engine_singleton
    if _engine_singleton is None:
        from apex.main import build_engine

        _engine_singleton = build_engine()
    return _engine_singleton


# Lifespan context manager for startup/shutdown
_MARKETPLACE_BACKEND = Path(__file__).resolve().parent / "autopilot-local" / "backend"
if str(_MARKETPLACE_BACKEND) not in sys.path:
    sys.path.insert(0, str(_MARKETPLACE_BACKEND))

_kalshi_ws_task: asyncio.Task | None = None
_kalshi_ws_mgr: Any = None
_background_scheduler: Any = None


def _morning_chain_enabled() -> bool:
    return os.getenv("APEX_MORNING_CHAIN", "true").lower() in ("1", "true", "yes")


def _scheduler_health() -> dict[str, Any]:
    """Report scheduler mode so daemon expectations are explicit."""
    loop_flags = {
        "arb_scan_loop": os.getenv("APEX_ARB_SCAN_LOOP", "false").lower() in ("1", "true", "yes"),
        "pm_agents_loop": os.getenv("APEX_PM_AGENTS_LOOP", "true").lower() in ("1", "true", "yes"),
        "equity_loop": os.getenv("APEX_EQUITY_LOOP", "true").lower() in ("1", "true", "yes"),
        "self_improvement_loop": os.getenv("APEX_SELF_IMPROVEMENT_LOOP", "false").lower()
        in ("1", "true", "yes"),
        "morning_chain": _morning_chain_enabled(),
    }
    in_process_enabled = any(loop_flags.values())
    daemon_expected = os.getenv("APEX_EXPECT_SCHEDULER_DAEMON", "false").lower() in (
        "1",
        "true",
        "yes",
    )
    daemon_running = False
    daemon_probe_error: str | None = None
    if daemon_expected:
        try:
            result = subprocess.run(
                ["ps", "-eo", "pid,args"],
                check=False,
                capture_output=True,
                text=True,
                timeout=2.0,
            )
            lines = (result.stdout or "").splitlines()
            daemon_running = any(
                (
                    "run_scheduler" in line
                    or "apex.scheduler.service" in line
                    or "apex.main:run_autopilot" in line
                )
                and "backend_api.py" not in line
                and "grep " not in line
                for line in lines
            )
        except Exception as exc:  # noqa: BLE001
            daemon_probe_error = str(exc)
    status = "ok"
    if daemon_expected and not daemon_running:
        status = "degraded"
    return {
        "mode": "in_process_loops" if in_process_enabled else "external_scheduler_only",
        "in_process_loops_enabled": in_process_enabled,
        "loops": loop_flags,
        "separate_process_expected": daemon_expected,
        "separate_process_running": daemon_running if daemon_expected else None,
        "status": status,
        "probe_error": daemon_probe_error,
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _kalshi_ws_task, _kalshi_ws_mgr, _background_scheduler
    from marketplace_lifecycle import shutdown_marketplace, startup_marketplace
    from apex.core.logging import get_logger
    from apex.demo.seed_data import seed_demo_database

    if settings.demo_mode:
        await asyncio.to_thread(seed_demo_database, store)
        get_logger(__name__).info("DEMO_MODE: database seeded for hackathon judges")
    elif settings.showcase_mode:
        from apex.demo.seed_data import seed_showcase_database

        await asyncio.to_thread(seed_showcase_database, store)
        get_logger(__name__).info(
            "SHOWCASE_MODE: seeded %d arbs / %d proposals",
            settings.showcase_arb_count,
            settings.showcase_proposal_count,
        )
    try:
        from apex.repositories.cftc_persistence import hydrate_tracker
        from apex.risk.metrics_service import get_cftc_tracker

        exposures = hydrate_tracker(store)
        if exposures:
            tracker = get_cftc_tracker()
            for ticker, notional in exposures.items():
                tracker.set_exposure(ticker, notional)
            print(f"[startup] Hydrated CFTC tracker: {len(exposures)} tickers")
    except Exception as exc:
        print(f"[startup] CFTC hydration skipped: {exc}")
    async def _start_kalshi_ws_feed() -> None:
        global _kalshi_ws_task, _kalshi_ws_mgr
        try:
            from apex.integrations.kalshi_adapter import KalshiEventClient
            from apex.integrations.kalshi_trading import kalshi_credentials_configured
            from apex.integrations.kalshi_ws import KalshiWsConnectionManager

            _ws_settings = get_settings()
            if not kalshi_credentials_configured(_ws_settings):
                return
            _kalshi_ws_mgr = KalshiWsConnectionManager(_ws_settings)
            try:
                _kc = KalshiEventClient(_ws_settings)
                markets = await asyncio.wait_for(
                    asyncio.to_thread(_kc.get_macro_markets, 5000, fast=True),
                    timeout=30.0,
                )
                _ws_tickers = [m.ticker for m in markets][:50]
            except Exception:
                _ws_tickers = []
            if _ws_tickers:
                _kalshi_ws_task = asyncio.create_task(_kalshi_ws_mgr.run(_ws_tickers))
                print(f"[startup] Kalshi WS L2 feed started: {len(_ws_tickers)} tickers")
        except Exception as exc:
            print(f"[startup] Kalshi WS L2 skipped (no keys or error): {exc}")

    asyncio.create_task(_start_kalshi_ws_feed())
    await startup_marketplace(enable_arb_worker=False)
    await asyncio.to_thread(cache.refresh)
    asyncio.create_task(data_refresh_loop())
    asyncio.create_task(ws_broadcast_loop())
    if os.getenv("APEX_ARB_SCAN_LOOP", "false").lower() in ("1", "true", "yes"):
        asyncio.create_task(arb_scan_loop())
    if os.getenv("APEX_PM_AGENTS_LOOP", "true").lower() in ("1", "true", "yes"):
        asyncio.create_task(pm_agents_loop())
    if os.getenv("APEX_EQUITY_LOOP", "true").lower() in ("1", "true", "yes"):
        asyncio.create_task(equity_autopilot_loop())
    if os.getenv("APEX_SELF_IMPROVEMENT_LOOP", "false").lower() in ("1", "true", "yes"):
        asyncio.create_task(self_improvement_loop())
    if _morning_chain_enabled():
        try:
            from apex.main import build_engine
            from apex.scheduler.service import start_background_scheduler

            engine = await asyncio.to_thread(build_engine)
            _background_scheduler = await asyncio.to_thread(start_background_scheduler, engine)
            print("[startup] Morning chain scheduler started (APScheduler, US/Eastern)")
        except Exception as exc:
            print(f"[startup] Morning chain scheduler failed: {exc}")
    try:
        yield
    finally:
        if _background_scheduler is not None:
            try:
                _background_scheduler.shutdown(wait=False)
            except Exception as exc:  # noqa: BLE001
                print(f"[shutdown] Morning chain scheduler: {exc}")
            _background_scheduler = None
        if _kalshi_ws_task and not _kalshi_ws_task.done():
            if _kalshi_ws_mgr is not None:
                _kalshi_ws_mgr.stop()
            _kalshi_ws_task.cancel()
            try:
                await _kalshi_ws_task
            except asyncio.CancelledError:
                pass
        await shutdown_marketplace()
        _ALPACA_POOL.shutdown(wait=False, cancel_futures=True)

app = FastAPI(title="APEX Trading Terminal API", version="1.0.0", lifespan=lifespan)


@app.middleware("http")
async def prometheus_request_counter(request, call_next):
    response = await call_next(request)
    try:
        from apex.observability.prometheus_metrics import APEX_REQUESTS

        if APEX_REQUESTS is not None:
            APEX_REQUESTS.labels(
                method=request.method,
                endpoint=request.url.path,
            ).inc()
    except Exception:
        pass
    return response

_CORS_ORIGINS = [
    o.strip()
    for o in (settings.cors_origins or "http://localhost:3000,http://127.0.0.1:3000").split(",")
    if o.strip()
]
if settings.public_demo_url:
    _CORS_ORIGINS.append(settings.public_demo_url.rstrip("/"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from agent.gateway import router as agent_router  # noqa: E402
from marketplace_integration import register_marketplace  # noqa: E402

app.include_router(agent_router)
register_marketplace(app)

# ---- Auth + security hardening --------------------------------------------
from fastapi.responses import JSONResponse  # noqa: E402
from apex.security.router import router as auth_router  # noqa: E402
from apex.security.deps import current_principal  # noqa: E402
from apex.security.ratelimit import SlidingWindowLimiter  # noqa: E402

app.include_router(auth_router)

# Public auth endpoints (no token required); everything else mutating is gated.
_PUBLIC_AUTH_PATHS = {
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/guest",
    "/api/auth/refresh",
    "/api/auth/logout",
}
# Sensitive prefixes require a real (non-guest) user.
_SENSITIVE_PREFIXES = ("/api/execute", "/api/ml", "/orders", "/api/orders")
_MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_api_limiter = SlidingWindowLimiter(
    max_events=int(settings.api_rate_limit_per_min), window_seconds=60.0
)


def _request_ip(request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@app.middleware("http")
async def security_gate(request, call_next):
    method = request.method.upper()
    path = request.url.path
    if settings.auth_enabled and method in _MUTATING_METHODS:
        ip = _request_ip(request)
        _api_limiter.max_events = int(settings.api_rate_limit_per_min)
        if not _api_limiter.allow(f"api:{ip}"):
            return JSONResponse(
                {"detail": "rate limit exceeded"},
                status_code=429,
                headers={"Retry-After": "5"},
            )
        # /api/auth/* manages its own authz (login/register public; keys via Depends).
        if path not in _PUBLIC_AUTH_PATHS and not path.startswith("/api/auth"):
            principal = current_principal(request, settings=settings)
            if principal is None:
                return JSONResponse(
                    {"detail": "authentication required"},
                    status_code=401,
                    headers={"WWW-Authenticate": "Bearer"},
                )
            if path.startswith(_SENSITIVE_PREFIXES) and principal.role not in {"user", "admin"}:
                return JSONResponse(
                    {"detail": "login required for this action"}, status_code=403
                )
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("X-XSS-Protection", "0")
    response.headers.setdefault("Cache-Control", "no-store")
    return response


def _normalize_account(raw: dict[str, Any]) -> dict[str, Any]:
    if not raw or raw.get("error"):
        return raw
    equity = float(raw.get("equity") or raw.get("portfolio_value") or 0)
    last_equity = float(raw.get("last_equity") or equity)
    daily_pl = float(raw.get("daily_pl") or (equity - last_equity))
    daily_pl_pct = float(
        raw.get("daily_pl_pct")
        or (daily_pl / last_equity * 100 if last_equity else 0)
    )
    return {
        "equity": equity,
        "buying_power": float(raw.get("buying_power") or 0),
        "cash": float(raw.get("cash") or 0),
        "portfolio_value": float(raw.get("portfolio_value") or equity),
        "daily_pl": daily_pl,
        "daily_pl_pct": daily_pl_pct,
        "status": raw.get("status", "unknown"),
    }


def _normalize_positions(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for p in rows or []:
        if not isinstance(p, dict):
            continue
        out.append(
            {
                "symbol": p.get("symbol", ""),
                "qty": float(p.get("qty") or 0),
                "market_value": float(p.get("market_value") or 0),
                "avg_entry_price": float(p.get("avg_entry_price") or 0),
                "current_price": float(p.get("current_price") or 0),
                "side": (p.get("side") or "long").lower(),
                "unrealized_pl": float(p.get("unrealized_pl") or 0),
                "unrealized_plpc": float(p.get("unrealized_plpc") or 0),
                "sector": p.get("sector", ""),
            }
        )
    return out


# REST API Endpoints
@app.get("/api/dashboard/snapshot")
def dashboard_snapshot():
    """Single round-trip for terminal overview (served from in-memory cache)."""
    cache.mark_stale_if_needed()
    return _ws_payload()


@app.get("/account")
def get_account():
    cache.mark_stale_if_needed()
    base = _normalize_account(cache._account or {})
    return {
        **base,
        "_data_age_seconds": cache._data_age_seconds,
        "_is_stale": cache._is_stale,
        "_last_update": cache._last_update,
    }

@app.get("/positions")
def get_positions():
    cache.mark_stale_if_needed()
    return _normalize_positions(cache._positions)

@app.get("/positions/closed")
def get_closed_positions():
    return cache._order_history

@app.get("/orders")
def get_orders(status: str = "open"):
    cache.mark_stale_if_needed()
    if status == "open":
        return cache._orders
    return cache._order_history

@app.get("/proposals")
def get_proposals():
    return cache._proposals

@app.get("/proposals/history")
def get_proposal_history():
    return cache._proposals

@app.get("/opportunities")
def get_opportunities():
    """Legacy endpoint — prefer /api/opportunities for ML-scored results."""
    return cache._opportunities

@app.get("/api/opportunities")
def list_api_opportunities(limit: int = 100):
    """ML-scored arb opportunities at the canonical /api/ path."""
    import time as _time

    from apex.ml.arb_edge_model import apply_model_scores

    now = _time.monotonic()
    with _arb_opps_lock:
        cached = _arb_opps_cache.get(limit)
        if cached and (now - cached[0]) < _ARB_OPPS_TTL_SEC:
            return cached[1]

    rows = store.list_arb_opportunities(limit=limit)
    scored = apply_model_scores(rows)

    with _arb_opps_lock:
        _arb_opps_cache[limit] = (now, scored)
    return scored

@app.get("/events")
def get_events(limit: int = 100):
    return list(cache._events)[:limit]

# Short TTL cache for the model-scored arb feed. The underlying rows only
# change when a scan persists (minutes apart), so caching for a few seconds
# removes redundant DB reads + ML scoring on bursty/polled requests.
_ARB_OPPS_TTL_SEC = float(os.getenv("APEX_ARB_OPPS_TTL_SEC", "5"))
_arb_opps_cache: dict[int, tuple[float, list]] = {}
_arb_opps_lock = threading.Lock()


@app.get("/api/arb/opportunities")
def list_arb_opportunities(limit: int = 100):
    import time as _time

    from apex.ml.arb_edge_model import apply_model_scores

    now = _time.monotonic()
    with _arb_opps_lock:
        cached = _arb_opps_cache.get(limit)
        if cached and (now - cached[0]) < _ARB_OPPS_TTL_SEC:
            return cached[1]

    rows = store.list_arb_opportunities(limit=limit)
    scored = apply_model_scores(rows)

    with _arb_opps_lock:
        _arb_opps_cache[limit] = (now, scored)
    return scored


def _latest_intelligence_report(ticker: str) -> Path | None:
    if not _INTEL_TICKER_RE.match(ticker):
        return None
    matches = sorted(_INTEL_REPORT_DIR.glob(f"{ticker}_*.json"), reverse=True)
    return matches[0] if matches else None


async def _run_intelligence_for_ticker(ticker: str) -> None:
    async with _INTEL_SEMAPHORE:
        try:
            rows = store.list_arb_opportunities(limit=500)
            row = next((r for r in rows if str(r.get("kalshi_ticker")) == ticker), None)
            if row is None:
                return
            from apex.domain.models import ArbOpportunity

            flags_raw = row.get("settlement_flags") or []
            if isinstance(flags_raw, str):
                try:
                    flags_raw = json.loads(flags_raw)
                except Exception:
                    flags_raw = [flags_raw]
            opp = ArbOpportunity(
                id=str(row.get("id")),
                kalshi_ticker=str(row.get("kalshi_ticker")),
                poly_market_id=str(row.get("poly_market_id")),
                question=str(row.get("question")),
                kalshi_title=str(row.get("kalshi_title")),
                poly_title=str(row.get("poly_title")),
                kalshi_yes_ask=float(row.get("kalshi_yes_ask") or 0.0),
                poly_no_ask=float(row.get("poly_no_ask") or 0.0),
                gross_spread=float(row.get("gross_spread") or 0.0),
                net_edge=float(row.get("net_edge") or 0.0),
                settlement_match_score=float(row.get("settlement_match_score") or 0.0),
                settlement_flags=list(flags_raw),
                volume_kalshi=float(row.get("volume_kalshi") or 0.0),
                volume_poly=float(row.get("volume_poly") or 0.0),
                category=str(row.get("category") or "UNKNOWN"),
                kelly_fraction=float(row.get("kelly_fraction") or 0.0),
            )
            intel = BrightDataIntelligence(settings)
            agent = ArbitrageIntelligenceAgent(settings, intel)
            await agent.run(opp)
        finally:
            _INTEL_IN_FLIGHT.discard(ticker)


@app.get("/api/intelligence/report/{ticker}")
def get_intelligence_report(ticker: str):
    latest = _latest_intelligence_report(ticker)
    if latest is None:
        raise HTTPException(status_code=404, detail="No report found for ticker")
    return json.loads(latest.read_text(encoding="utf-8"))


@app.post("/api/intelligence/run/{ticker}", status_code=202)
async def run_intelligence_report(
    ticker: str,
    x_intelligence_override: str | None = Header(default=None),
    x_intelligence_token: str | None = Header(default=None),
):
    ticker = ticker.strip().upper()
    if not _INTEL_TICKER_RE.match(ticker):
        raise HTTPException(status_code=400, detail="Invalid ticker format")
    expected_token = (os.getenv("INTELLIGENCE_RUN_TOKEN") or "").strip()
    if expected_token:
        if x_intelligence_token != expected_token:
            raise HTTPException(status_code=403, detail="Missing or invalid intelligence token")
    elif not settings.demo_mode:
        raise HTTPException(
            status_code=403,
            detail="INTELLIGENCE_RUN_TOKEN must be configured for non-demo runs.",
        )
    if settings.demo_mode and x_intelligence_override != "allow-demo-credits":
        raise HTTPException(
            status_code=403,
            detail="Blocked in DEMO_MODE. Send x-intelligence-override=allow-demo-credits to proceed.",
        )
    async with _INTEL_IN_FLIGHT_LOCK:
        if ticker in _INTEL_IN_FLIGHT:
            raise HTTPException(status_code=409, detail="Intelligence run already in progress for ticker")
        _INTEL_IN_FLIGHT.add(ticker)
    asyncio.create_task(_run_intelligence_for_ticker(ticker))
    return {"accepted": True, "ticker": ticker}

@app.get("/api/risk/metrics")
def get_risk_metrics():
    """Week 6: VIX, Monte Carlo VaR, CFTC limits, Kelly samples."""
    from apex.risk.metrics_service import build_risk_metrics

    cache.mark_stale_if_needed()
    account = _normalize_account(cache._account or {})
    equity = float(account.get("equity") or 100_000.0)
    positions = _normalize_positions(cache._positions or [])
    arbs = store.list_arb_opportunities(limit=100)
    return build_risk_metrics(
        account_equity=equity,
        positions=positions,
        arb_opportunities=arbs,
        kelly_alpha=float(getattr(settings, "kelly_alpha", 0.25)),
        kelly_lambda=float(getattr(settings, "kelly_lambda", 0.02)),
    )


@app.get("/api/arb/summary")
def get_arb_summary():
    active = store.list_arb_opportunities(limit=1000)
    resolved = store.get_resolved_arb_opportunities(limit=1000)
    wins = len([o for o in resolved if (o.pnl or 0) > 0])
    total = len(resolved)
    win_rate = (wins / total) if total > 0 else 0.0
    return {
        "active_opportunities": len(active),
        "resolved_opportunities": total,
        "win_rate": win_rate,
    }

@app.get("/api/arb/backtest")
def get_arb_backtest(lookback_days: int = 90):
    from dataclasses import asdict
    from apex.services.backtest_engine import BacktestEngine
    engine = BacktestEngine(settings=settings, store=store)
    result = engine.run(lookback_days=lookback_days)
    return asdict(result)

@app.get("/api/arb/{arb_id}")
def get_arb_opportunity(arb_id: str):
    row = store.get_arb_opportunity(arb_id)
    if not row:
        return {"error": "not_found", "id": arb_id}
    return row

@app.get("/api/arb/{arb_id}/thesis")
async def stream_arb_thesis(arb_id: str):
    opp_dict = store.get_arb_opportunity(arb_id)
    if not opp_dict:
        raise HTTPException(status_code=404, detail="Arb opportunity not found")

    async def event_generator():
        client = settings.get_llm_client()
        if client is None:
            yield f"data: {json.dumps({'token': 'Error: No LLM client configured.'})}\n\n"
            yield "data: [DONE]\n\n"
            return

        import dataclasses
        import asyncio as _asyncio
        from apex.layers.l2.arb_analyst_panel import ArbAnalystPanel
        from apex.domain.models import ArbOpportunity

        opp = ArbOpportunity(
            id=opp_dict["id"],
            kalshi_ticker=opp_dict["kalshi_ticker"],
            poly_market_id=opp_dict["poly_market_id"],
            question=opp_dict["question"],
            kalshi_title=opp_dict["kalshi_title"],
            poly_title=opp_dict["poly_title"],
            kalshi_yes_ask=opp_dict["kalshi_yes_ask"],
            poly_no_ask=opp_dict["poly_no_ask"],
            gross_spread=opp_dict["gross_spread"],
            net_edge=opp_dict["net_edge"],
            settlement_match_score=opp_dict["settlement_match_score"],
            settlement_flags=json.loads(opp_dict["settlement_flags"] or "[]"),
            volume_kalshi=opp_dict.get("volume_kalshi", 0.0),
            volume_poly=opp_dict.get("volume_poly", 0.0),
        )

        try:
            panel = ArbAnalystPanel(settings)
            thesis = await panel.evaluate(opp)
            full_json_str = json.dumps(dataclasses.asdict(thesis), indent=2)
            chunk_size = 32
            for i in range(0, len(full_json_str), chunk_size):
                chunk = full_json_str[i:i+chunk_size]
                yield f"data: {json.dumps({'token': chunk})}\n\n"
                await _asyncio.sleep(0.05)
        except Exception as exc:
            yield f"data: {json.dumps({'token': f'Error generating thesis: {exc}'})}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/arb/{arb_id}/thesis_stream")
async def stream_arb_thesis_llm(arb_id: str):
    row = store.get_arb_opportunity(arb_id) or {}
    question = row.get("question") or "Cross-market arb"
    edge = row.get("net_edge") or 0.0
    direction = row.get("direction") or "unknown"

    prompt = (
        f"Analyze opportunity: {question}. Direction: {direction}. Estimated edge: {edge}."
    )

    async def generate():
        yield _sse_event("start", {"arb_id": arb_id})
        async for token in thesis_client.stream_thesis(prompt):
            yield _sse_event("delta", {"text": token})
        yield _sse_event("done", {"status": "ok"})

    return StreamingResponse(generate(), media_type="text/event-stream")

@app.post("/api/execute/scratch")
async def execute_scratch(payload: dict):
    """Week 7: Kalshi leg scratch / auto-reversal."""
    from apex.execution.scratch import submit_scratch_close

    ticker = (payload or {}).get("ticker") or (payload or {}).get("kalshi_ticker")
    if not ticker:
        raise HTTPException(status_code=400, detail="ticker required")
    return submit_scratch_close(
        str(ticker),
        side=str((payload or {}).get("side", "yes")),
        size=int((payload or {}).get("size", 10)),
        limit_price=(payload or {}).get("limit_price"),
    )


@app.post("/api/execute/state-machine")
async def run_execution_state_machine(payload: dict):
    """Week 7: paper dual-leg state machine."""
    from apex.execution.state_machine import ArbExecutionStateMachine

    arb_id = str((payload or {}).get("arb_id", "paper"))
    sm = ArbExecutionStateMachine(arb_id)
    ctx = sm.run_paper_flow(
        leg1_fill=lambda: f"kalshi-{arb_id}",
        leg2_fill=lambda: f"poly-{arb_id}",
        simulate_mev=bool((payload or {}).get("simulate_mev")),
    )
    return {"state": ctx.state, "history": ctx.history}


@app.post("/api/agents/consensus")
async def agents_consensus(payload: dict):
    """Week 8: hive-mind vote on trade."""
    from apex.agents.consensus_engine import ConsensusEngine

    return ConsensusEngine().evaluate(payload or {}).to_dict()


@app.get("/metrics")
def prometheus_metrics():
    """Week 9: Prometheus scrape endpoint."""
    from fastapi.responses import Response
    from apex.observability.prometheus_metrics import metrics_payload

    return Response(metrics_payload(), media_type="text/plain; version=0.0.4")


@app.get("/api/fund/tearsheet")
def fund_tearsheet():
    """Week 10: PDF tear-sheet."""
    from fastapi.responses import Response
    from apex.fund.tearsheet import generate_tearsheet_pdf
    from apex.risk.metrics_service import build_risk_metrics

    cache.mark_stale_if_needed()
    account = _normalize_account(cache._account or {})
    metrics = build_risk_metrics(account_equity=float(account.get("equity") or 0))
    pdf = generate_tearsheet_pdf(
        {"equity": metrics["account_equity"], "var_99_usd": metrics["var"]["var_99_usd"], "vix": metrics["vix"]}
    )
    return Response(pdf, media_type="application/pdf")


@app.post("/api/execute/sor")
async def execute_sor(payload: dict):
    """Smart Order Router — paper routing (Week 2 Day 5)."""
    from apex.execution.sor import build_sor_from_payload, execute_sor_paper

    req = build_sor_from_payload(payload or {})
    if not req.arb_id:
        raise HTTPException(status_code=400, detail="arb_id required")
    if not req.legs:
        raise HTTPException(status_code=400, detail="legs required")
    return execute_sor_paper(req)


@app.get("/api/defi/treasury")
def defi_treasury_status():
    """DeFi treasury paper status (Phase 4)."""
    from apex.defi.treasury import treasury_status

    return treasury_status()


@app.get("/api/cross-asset/signals")
def cross_asset_signals():
    """Cross-asset hedge mapping signals (Week 3)."""
    from apex.cross_asset.mapping import CROSS_ASSET_MAP

    return {"mappings": CROSS_ASSET_MAP}


@app.get("/api/orderbook/{venue}/{ticker}")
def get_l2_orderbook(venue: str, ticker: str):
    """Redis L2 orderbook snapshot (Week 1)."""
    from apex.cache.orderbook_l2 import read_orderbook

    book = read_orderbook(venue.upper(), ticker)
    if not book:
        raise HTTPException(status_code=404, detail="Orderbook not in cache")
    return book


@app.get("/api/arb/metrics")
def arb_scan_metrics():
    """Latency observability for the arb scan hot path (fetch/match/total ms,
    coalesce hit-rate, rolling averages)."""
    from apex.observability import scan_metrics

    return scan_metrics.snapshot()


@app.post("/api/arb/scan")
async def trigger_arb_scan():
    """Manual arb scan (same as scheduler loop)."""
    from apex.services.arb_scan import scan_and_persist

    scan_timeout = float(os.getenv("ARB_SCAN_TIMEOUT_SEC", "90"))
    try:
        opps = await asyncio.wait_for(
            asyncio.to_thread(scan_and_persist, store, limit=50, ingest_l2=False),
            timeout=scan_timeout,
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Arb scan timed out")
    return {"status": "ok", "count": len(opps)}


@app.get("/api/pm/brain")
def pm_brain(force: bool = False):
    """Kalshi + Polymarket brain snapshot for dashboard (45s TTL cache)."""
    from apex.services.pm_brain import build_pm_brain

    return build_pm_brain(store, force=force)


@app.get("/api/brain/status")
def brain_status(probe: bool = False):
    """FinanceBrain (autopilot LLM reasoner) status + optional live API probe."""
    from apex.brain import get_brain

    return get_brain(settings, refresh=True).status(probe=probe)


@app.post("/api/brain/ask")
def brain_ask(payload: dict = Body(...)):
    """Ask the finance brain a question grounded in the strategy knowledge base."""
    from apex.brain import get_brain

    question = str((payload or {}).get("question", "")).strip()
    if not question:
        raise HTTPException(status_code=400, detail="question is required")
    if len(question) > 2000:
        raise HTTPException(status_code=413, detail="question too long")
    context = payload.get("context")
    context = str(context)[:8000] if context else None
    answer = get_brain(settings).ask(question, context=context)
    return {"answer": answer, "source": get_brain(settings).route_label}


@app.get("/api/brain/analyze/{arb_id}")
def brain_analyze(arb_id: str):
    """Structured FinanceBrain verdict for a stored arb opportunity."""
    from apex.brain import get_brain

    row = store.get_arb_opportunity(arb_id)
    if not row:
        raise HTTPException(status_code=404, detail="Arb opportunity not found")
    verdict = get_brain(settings).analyze_opportunity(row)
    return {"arb_id": arb_id, **verdict.to_dict()}


@app.get("/api/kalshi/book")
def kalshi_book():
    """Kalshi prediction-market paper book (not copy trading)."""
    from apex.services.prediction_books import build_kalshi_book

    return build_kalshi_book(store)


@app.get("/api/polymarket/book")
def polymarket_book():
    """Polymarket prediction-market paper book from APEX audit (not copy trading)."""
    from apex.services.prediction_books import build_polymarket_book

    return build_polymarket_book(store)


@app.get("/api/pm/agents/status")
def pm_agents_status():
    from apex.services.pm_trading import pm_agents_status as _status

    try:
        return _status(get_cached_engine(), store)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"PM agent status unavailable: {exc}") from exc


@app.post("/api/pm/polymarket/run-agents")
async def run_polymarket_agents():
    """Run Polymarket discovery + optional automated paper submission."""
    from apex.services.pm_trading import run_polymarket_agent_cycle

    engine = get_cached_engine()
    return await asyncio.to_thread(run_polymarket_agent_cycle, engine)


@app.post("/api/pm/kalshi/run-agents")
async def run_kalshi_agents():
    """Run Kalshi↔Poly arb scan + optional automated dual-leg paper trades."""
    from apex.services.pm_trading import run_kalshi_arb_agent_cycle

    return await run_kalshi_arb_agent_cycle(get_cached_engine())


@app.get("/api/ml/status")
def ml_status_endpoint():
    from apex.services.self_improvement import ml_status

    return ml_status(store)


@app.post("/api/ml/export")
def ml_export_endpoint():
    from apex.services.training_export import export_training_corpus

    return export_training_corpus(store=store)


@app.post("/api/ml/train")
def ml_train_endpoint():
    from apex.services.self_improvement import run_train_candidate

    return run_train_candidate(store)


@app.post("/api/ml/evaluate")
def ml_evaluate_endpoint(force: bool = False):
    from apex.services.self_improvement import run_evaluate_promote

    return run_evaluate_promote(store, force=force)


@app.post("/api/ml/run-cycle")
async def ml_run_cycle_endpoint():
    from apex.services.self_improvement import run_self_improvement_cycle

    timeout = float(os.getenv("SELF_IMPROVEMENT_CYCLE_TIMEOUT_SEC", "180"))
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(run_self_improvement_cycle, get_cached_engine()),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Self-improvement cycle timed out")


@app.post("/api/pm/agents/run")
async def run_pm_agents():
    """Run both Polymarket event agent and Kalshi arb agent."""
    from apex.services.pm_trading import run_prediction_markets_agent_cycle

    timeout = float(os.getenv("PM_AGENT_CYCLE_TIMEOUT_SEC", "120"))
    try:
        return await asyncio.wait_for(
            run_prediction_markets_agent_cycle(get_cached_engine(), fast_scan=True),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="PM agent cycle timed out")


@app.get("/api/world-cup/status")
def world_cup_status_endpoint():
    from apex.services.world_cup_trading import world_cup_status

    return world_cup_status(store)


@app.get("/api/world-cup/simulation")
def world_cup_simulation(n: int = 1000):
    """Paper read-only Monte Carlo tournament win probabilities (no execution)."""
    from apex.ml.wc_tournament_sim import MODEL_VERSION, run_monte_carlo, top_teams

    n_sims = max(1, min(int(n), 10_000))
    probs = run_monte_carlo(n_sims, settings)
    return {
        "paper": True,
        "read_only": True,
        "model_version": MODEL_VERSION,
        "n_sims": n_sims,
        "top_teams": top_teams(probs, limit=20),
    }


@app.get("/api/world-cup/opportunities")
def world_cup_opportunities(limit: int = 100):
    from apex.ml.world_cup_model import apply_scores

    rows = store.list_world_cup_opportunities(limit=limit)
    if not rows:
        from apex.services.world_cup_trading import discover_and_persist

        rows = discover_and_persist(store)
    return apply_scores(rows, settings)


@app.post("/api/world-cup/discover")
def world_cup_discover():
    from apex.services.world_cup_trading import discover_and_persist

    rows = discover_and_persist(store)
    return {"count": len(rows), "opportunities": rows[:50]}


@app.post("/api/world-cup/run-cycle")
async def world_cup_run_cycle():
    from apex.services.world_cup_trading import run_world_cup_agent_cycle

    timeout = float(os.getenv("WORLD_CUP_CYCLE_TIMEOUT_SEC", "120"))
    try:
        return await asyncio.wait_for(
            run_world_cup_agent_cycle(get_cached_engine()),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="World Cup cycle timed out")


@app.post("/api/world-cup/paper-trade")
async def world_cup_paper_trade(payload: dict):
    body = payload or {}
    venue = str(body.get("venue") or "kalshi").lower()
    if venue == "polymarket":
        from apex.services.pm_trading import place_polymarket_paper_leg

        return await place_polymarket_paper_leg(
            get_cached_engine(),
            market_id=str(body.get("market_id") or ""),
            outcome=str(body.get("outcome") or "YES"),
            stake_usd=float(body.get("stake_usd") or 50),
            price=float(body.get("price") or 0.5),
            question=str(body.get("question") or ""),
        )
    from apex.services.pm_trading import place_kalshi_paper_leg

    return await place_kalshi_paper_leg(
        get_cached_engine(),
        ticker=str(body.get("ticker") or ""),
        stake_usd=float(body.get("stake_usd") or 50),
        price=float(body.get("price") or 0.5),
        question=str(body.get("question") or ""),
    )


@app.post("/api/kalshi/paper-trade")
async def kalshi_paper_trade(payload: dict):
    from apex.services.pm_trading import place_kalshi_paper_leg

    body = payload or {}
    ticker = str(body.get("ticker") or "").strip()
    if not ticker:
        raise HTTPException(status_code=400, detail="ticker required")
    return await place_kalshi_paper_leg(
        get_cached_engine(),
        ticker=ticker,
        stake_usd=float(body.get("stake_usd") or 50),
        price=float(body.get("price") or 0.5),
        question=str(body.get("question") or ""),
    )


@app.post("/api/polymarket/paper-trade")
async def polymarket_paper_trade(payload: dict):
    from apex.services.pm_trading import place_polymarket_paper_leg

    body = payload or {}
    market_id = str(body.get("market_id") or "").strip()
    if not market_id:
        raise HTTPException(status_code=400, detail="market_id required")
    return await place_polymarket_paper_leg(
        get_cached_engine(),
        market_id=market_id,
        outcome=str(body.get("outcome") or "YES"),
        stake_usd=float(body.get("stake_usd") or 50),
        price=float(body.get("price") or 0.5),
        question=str(body.get("question") or ""),
    )


@app.post("/api/arb/{arb_id}/paper-trade")
async def paper_trade_arb(arb_id: str):
    opp_dict = store.get_arb_opportunity(arb_id)
    if not opp_dict:
        raise HTTPException(status_code=404, detail="Arb opportunity not found")

    from dataclasses import fields

    from apex.domain.models import ArbOpportunity

    allowed = {f.name for f in fields(ArbOpportunity)}
    payload = {k: v for k, v in opp_dict.items() if k in allowed}
    if "detection_ts" not in payload and opp_dict.get("detected_at"):
        payload["detection_ts"] = opp_dict["detected_at"]
    opp = ArbOpportunity(**payload)
    opp.settlement_flags = json.loads(opp_dict.get("settlement_flags") or "[]")

    if settings.demo_mode or arb_id == "demo-reject-demo":
        if arb_id == "demo-reject-demo" or (opp.net_edge or 0) < 0.01:
            raise HTTPException(
                status_code=400,
                detail="Risk failed: M07 insufficient liquidity (demo rejection path)",
            )
        from apex.domain.enums import EventType
        from apex.domain.models import AuditEvent

        kid = f"demo-kalshi-{arb_id[:8]}"
        pid = f"demo-poly-{arb_id[:8]}"
        store.append_event(
            AuditEvent(
                event_type=EventType.ARB_PAPER_SUBMITTED,
                symbol=opp.kalshi_ticker,
                order_id=kid,
                conviction=7.0,
                raw_payload={
                    "arb_id": arb_id,
                    "kalshi_order_id": kid,
                    "poly_order_id": pid,
                    "demo_mode": True,
                },
            )
        )
        return {"status": "ok", "kalshi_order_id": kid, "poly_order_id": pid, "demo_mode": True}

    engine = get_cached_engine()
    stake = float(opp_dict.get("kelly_stake_usd") or 50.0)
    risk = engine.execution.risk_engine.run_arb_paper(opp, stake_usd=stake)
    if not risk.all_passed:
        raise HTTPException(
            status_code=400,
            detail=risk.rejection_reason or f"Risk failed: {risk.failed}",
        )

    kalshi_id, poly_id = await engine.execution.submit_arb_paper_orders(opp, thesis=None)
    if not kalshi_id:
        raise HTTPException(status_code=400, detail="Paper trade execution failed")

    return {"status": "ok", "kalshi_order_id": kalshi_id, "poly_order_id": poly_id}


@app.post("/api/arb/{arb_id}/thesis/chat")
async def thesis_chat(arb_id: str, payload: dict):
    opp_dict = store.get_arb_opportunity(arb_id)
    if not opp_dict:
        raise HTTPException(status_code=404, detail="Arb opportunity not found")

    client = settings.get_llm_client()
    if not client:
        raise HTTPException(status_code=500, detail="LLM not configured")

    user_msg = (payload or {}).get("message", "")
    if not user_msg:
        raise HTTPException(status_code=400, detail="Message required")

    prompt = (
        f"Context about the arb: {json.dumps(opp_dict, default=str)}\n\n"
        f"User Question: {user_msg}\n\n"
        "Please answer the user's question briefly."
    )

    try:
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model=getattr(settings, "llm_model", "gpt-4o"),
            messages=[{"role": "user", "content": prompt}],
            max_tokens=256,
        )
        reply = response.choices[0].message.content
        return {"reply": reply}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@app.websocket("/api/arb/stream")
async def stream_arb_updates(websocket: WebSocket):
    """RFC 6902 JSON Patch stream (Week 1) with legacy full-sync fallback."""
    await websocket.accept()
    poll_sec = float(os.getenv("ARB_STREAM_POLL_SEC", "1"))
    use_patches = os.getenv("ARB_STREAM_USE_PATCHES", "true").lower() in ("1", "true", "yes")

    from apex.services.arb_row_utils import normalize_arb_rows

    def fetch_rows() -> list[dict]:
        from apex.services.arb_row_utils import normalize_arb_row
        from dataclasses import asdict

        rows = normalize_arb_rows(store.read_table("arb_opportunities", limit=200))
        if settings.demo_mode:
            try:
                from apex.services.arb_engine import ArbEngine

                engine = ArbEngine(settings=settings, store=store)
                live = [normalize_arb_row(asdict(o)) for o in engine.scan()]
                if live:
                    return sorted(live, key=lambda r: -(r.get("net_edge") or 0))
            except Exception as exc:
                print(f"demo_mode scan fallback to sqlite: {exc}")
        from apex.ml.arb_edge_model import apply_model_scores

        return apply_model_scores(rows)

    def status_payload(rows: list[dict]) -> dict:
        edges = [float(o.get("net_edge") or 0) for o in rows]
        return {
            "type": "status",
            "polling_rate_sec": poll_sec,
            "max_edge": max(edges) if edges else 0,
            "count": len(rows),
            "patch_mode": use_patches,
            "demo_mode": settings.demo_mode,
        }

    from apex.streaming.arb_patch_stream import ArbPatchStream

    patch_stream = ArbPatchStream()
    last_max_edge = -1.0
    tick = 0
    try:
        while True:
            opportunities = await asyncio.to_thread(fetch_rows)
            force_full = tick == 0
            if use_patches:
                msg = patch_stream.build_message(opportunities, force_full=force_full)
                if msg.get("type") != "heartbeat":
                    await websocket.send_json(msg)
            else:
                await websocket.send_json({"type": "sync", "opportunities": opportunities})
            edges = [float(o.get("net_edge") or 0) for o in opportunities]
            max_edge = max(edges) if edges else 0
            tick += 1
            if tick == 1 or max_edge != last_max_edge or tick % 5 == 0:
                await websocket.send_json(status_payload(opportunities))
                last_max_edge = max_edge
            await asyncio.sleep(poll_sec)
    except WebSocketDisconnect:
        return
    except Exception as exc:
        print(f"arb stream error: {exc}")
        await websocket.close()

@app.get("/account/history")
def get_account_history(days: int = 30):
    """Get historical account equity data for equity curve chart."""
    equity_data = store.get_equity_curve(days=days)

    if equity_data:
        return [
            {
                "time": int(datetime.fromisoformat(row["timestamp"]).replace(tzinfo=timezone.utc).timestamp() * 1000),
                "equity": float(row["equity"]),
                "portfolio_value": float(row.get("positions_value", 0)),
            }
            for row in equity_data
        ]

    return []

def _chart_bars_with_time(bars: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for bar in bars:
        raw_date = bar.get("date") or bar.get("time")
        if raw_date is None:
            continue
        if isinstance(raw_date, (int, float)):
            ts_ms = int(raw_date)
        else:
            try:
                dt = datetime.fromisoformat(str(raw_date).replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                ts_ms = int(dt.timestamp() * 1000)
            except ValueError:
                continue
        out.append(
            {
                "time": ts_ms,
                "open": float(bar.get("open", 0)),
                "high": float(bar.get("high", 0)),
                "low": float(bar.get("low", 0)),
                "close": float(bar.get("close", 0)),
                "volume": float(bar.get("volume", 0)),
            }
        )
    return out


def _fetch_chart(symbol: str, timeframe: str) -> list[dict[str, Any]]:
    bars, _source = get_chart_bars(symbol, timeframe)
    if not bars:
        raise HTTPException(status_code=404, detail="No market data available")
    return bars


def _fetch_options(symbol: str) -> dict[str, Any]:
    chain = get_options_chain(symbol)

    calls = []
    puts = []
    for c in chain.get("calls", [])[:15]:
        calls.append({
            "strike": float(c.get("strike", 0)),
            "bid": float(c.get("bid", 0)),
            "ask": float(c.get("ask", 0)),
            "last": float(c.get("lastPrice", 0)),
            "change": float(c.get("change", 0)),
            "volume": int(c.get("volume", 0)),
            "open_interest": int(c.get("openInterest", 0)),
            "implied_volatility": float(c.get("impliedVolatility", 0)),
            "delta": float(c.get("delta", 0)),
            "gamma": float(c.get("gamma", 0)),
            "theta": float(c.get("theta", 0)),
            "vega": float(c.get("vega", 0)),
        })
    for p in chain.get("puts", [])[:15]:
        puts.append({
            "strike": float(p.get("strike", 0)),
            "bid": float(p.get("bid", 0)),
            "ask": float(p.get("ask", 0)),
            "last": float(p.get("lastPrice", 0)),
            "change": float(p.get("change", 0)),
            "volume": int(p.get("volume", 0)),
            "open_interest": int(p.get("openInterest", 0)),
            "implied_volatility": float(p.get("impliedVolatility", 0)),
            "delta": float(p.get("delta", 0)),
            "gamma": float(p.get("gamma", 0)),
            "theta": float(p.get("theta", 0)),
            "vega": float(p.get("vega", 0)),
        })

    if not calls and not puts:
        raise HTTPException(status_code=404, detail="No options data available")

    return {
        "symbol": symbol,
        "expiry": chain.get("expiry", ""),
        "calls": calls,
        "puts": puts,
    }


@app.get("/chart/{symbol}")
async def get_chart(symbol: str, timeframe: str = "1D"):
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_fetch_chart, symbol.upper(), timeframe),
            timeout=45.0,
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Chart data timed out") from None
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Market data unavailable: {exc}") from exc


@app.get("/options/{symbol}")
async def get_option_chain(symbol: str):
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_fetch_options, symbol.upper()),
            timeout=45.0,
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Options data timed out") from None
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Options data unavailable: {exc}") from exc

def _health_payload() -> dict[str, Any]:
    cache.mark_stale_if_needed()
    account = _normalize_account(cache._account or {})
    account_status = account.get("status")
    if isinstance(account_status, str):
        account_status = account_status.lower()
    is_alpaca_ok = cache._alpaca_connected and account_status not in {"error", "exception"}
    feeds = probe_market_feeds(settings)
    opportunities_count = len(cache._opportunities or [])
    proposals_count = len(cache._proposals or [])
    events_count = len(cache._events or [])
    arb_active = 0
    try:
        arb_active = len(store.list_arb_opportunities(limit=500))
        opportunities_count = max(opportunities_count, arb_active)
    except Exception:
        pass
    ml_block: dict = {}
    try:
        from apex.services.self_improvement import ml_status

        ml_block = ml_status(store)
    except Exception:
        ml_block = {}
    def _finite_or_none(value: Any) -> float | None:
        try:
            num = float(value)
        except Exception:
            return None
        return num if math.isfinite(num) else None

    kalshi_ws_block: dict[str, Any] = {
        "connected": _kalshi_ws_task is not None and not _kalshi_ws_task.done(),
        "stale": _kalshi_ws_mgr.is_stale if _kalshi_ws_mgr is not None else None,
        "seconds_since_message": _finite_or_none(_kalshi_ws_mgr.seconds_since_last_message)
        if _kalshi_ws_mgr is not None
        else None,
        "seconds_since_frame": _finite_or_none(_kalshi_ws_mgr.seconds_since_last_frame)
        if _kalshi_ws_mgr is not None
        else None,
        "reconnects": getattr(_kalshi_ws_mgr, "_reconnect_count", 0) if _kalshi_ws_mgr else 0,
    }
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "last_cache_update": cache._last_update,
        "data_age_seconds": cache._data_age_seconds,
        "is_stale": cache._is_stale,
        "demo_mode": settings.demo_mode,
        "alpaca_connected": is_alpaca_ok,
        "yfinance_ok": feeds["yfinance"]["available"],
        "market_feeds": feeds,
        "positions": len(cache._positions or []),
        "orders": len(cache._orders or []),
        "opportunities": opportunities_count,
        "proposals": proposals_count,
        "events": events_count,
        "arb_opportunities": arb_active,
        "showcase_mode": settings.showcase_mode,
        "ml": ml_block,
        "kalshi_ws": kalshi_ws_block,
        "scheduler": _scheduler_health(),
    }


@app.get("/")
def root():
    """Service index — API has no HTML UI; terminal lives on the frontend service."""
    links: dict[str, str] = {
        "health": "/health",
        "docs": "/docs",
        "openapi": "/openapi.json",
        "arb_opportunities": "/api/arb/opportunities",
    }
    out: dict[str, object] = {
        "service": "apex-autopilot-api",
        "message": "Backend API only. Open the frontend URL for the trading terminal.",
        "links": links,
    }
    frontend_url = os.getenv("FRONTEND_URL", "").strip() or (
        settings.public_demo_url.strip() if settings.public_demo_url else ""
    )
    if frontend_url:
        out["frontend"] = frontend_url.rstrip("/")
    return out


@app.get("/health")
def health():
    return _health_payload()


@app.get("/api/health")
def api_health():
    """Settings UI compatibility — engine health + copy-trading refresh logs."""
    from marketplace_integration import marketplace_health

    h = _health_payload()
    account = _normalize_account(cache._account or {})
    market = marketplace_health()
    last_refresh = dict(market.get("last_refresh") or {})
    if h.get("last_cache_update"):
        last_refresh.setdefault("engine", h["last_cache_update"])
    alpaca = market.get("alpaca") or {}
    if not alpaca.get("equity") and account.get("equity") is not None:
        alpaca = {
            **alpaca,
            "equity": account.get("equity"),
            "status": "connected" if h["alpaca_connected"] else "disconnected",
        }
    return {
        "alpaca": alpaca,
        "last_refresh": last_refresh,
        "timestamp": market.get("timestamp") or h["timestamp"],
        "engine": h,
        "demo_mode": settings.demo_mode,
    }


@app.get("/api/demo/status")
def demo_status():
    """Hackathon judge endpoint — confirms demo seed and paper-only mode."""
    opps = store.list_arb_opportunities(limit=50)
    return {
        "demo_mode": settings.demo_mode,
        "paper_only": bool(settings.alpaca_paper_trade),
        "public_demo_url": settings.public_demo_url or None,
        "arb_opportunities": len(opps),
        "sqlite_path": str(settings.sqlite_path),
    }

@app.get("/integrations")
async def integrations(force: bool = False):
    from apex.services.integration_status import build_integrations_status

    return await asyncio.wait_for(
        asyncio.to_thread(build_integrations_status, force=force),
        timeout=12.0,
    )

# Order submission endpoint
@app.post("/orders")
async def submit_order(order: dict):
    alpaca = _alpaca()
    if not alpaca.available:
        return {"error": "Alpaca not configured", "status": "failed"}
    
    symbol = order.get("symbol", "")
    qty = float(order.get("qty", 0))
    side = order.get("side", "buy")
    order_type = order.get("type", "market")
    time_in_force = order.get("time_in_force", "day")
    limit_price = order.get("limit_price")
    
    result = alpaca.place_order(
        symbol=symbol,
        qty=qty,
        side=side,
        order_type=order_type,
        time_in_force=time_in_force,
        limit_price=limit_price,
    )
    
    await asyncio.to_thread(cache.refresh)
    
    return result

@app.post("/orders/{order_id}/cancel")
async def cancel_order(order_id: str):
    alpaca = _alpaca()
    if not alpaca.available:
        return {"error": "Alpaca not configured", "status": "failed"}
    
    result = alpaca.cancel_order(order_id)
    await asyncio.to_thread(cache.refresh)
    return result

# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        initial = _ws_payload()
        initial["type"] = "initial_data"
        await websocket.send_json(initial)

        async def heartbeat():
            while True:
                await asyncio.sleep(15)
                try:
                    pong = {"type": "heartbeat", "timestamp": datetime.now(timezone.utc).isoformat()}
                    await websocket.send_json(pong)
                except Exception:
                    break

        hb_task = asyncio.create_task(heartbeat())
        try:
            while True:
                try:
                    raw = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)
                except asyncio.TimeoutError:
                    await websocket.send_json({"type": "pong"})
                    continue
                if raw in ("ping", '{"type":"ping"}'):
                    await websocket.send_json({"type": "pong"})
        finally:
            hb_task.cancel()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)

# Manual refresh endpoint
@app.post("/refresh")
async def refresh_data():
    await asyncio.wait_for(asyncio.to_thread(cache.refresh), timeout=30.0)
    from apex.services.integration_status import build_integrations_status

    await asyncio.to_thread(build_integrations_status, force=True)
    return {
        "status": "refreshed",
        "timestamp": cache._last_update,
        "is_stale": cache._is_stale,
    }

# Prometheus Metrics endpoint
from fastapi.responses import PlainTextResponse  # noqa: E402

@app.get("/metrics", response_class=PlainTextResponse)
def metrics():
    from apex.monitoring.metrics import get_metrics
    m = get_metrics()
    m.set_gauge("apex_equity", cache._account.get("equity", 0))
    m.set_gauge("apex_positions", len(cache._positions))
    m.set_gauge("apex_opportunities", len(cache._opportunities))
    m.set_gauge("apex_events", len(cache._events))
    return m.render_prometheus()


# Helper to proxy Discord-related requests to a separate Discord service
def _discord_proxy_get(path: str, params: dict | None = None) -> dict:
    """Proxy GET to external Discord service defined by DISCORD_SERVICE_URL.
    Falls back to local Discord integration only if DISCORD_SERVICE_URL is unset
    and the local integration is importable. This keeps the main API decoupled.
    """
    svc = os.getenv("DISCORD_SERVICE_URL")
    if svc:
        url = svc.rstrip("/") + path
        try:
            r = requests.get(url, params=params or {}, timeout=5)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            return {"error": f"discord service proxy error: {e}", "_url": url}

    # Fallback: attempt local import (legacy single-process mode)
    try:
        # local integration exposes the same interface as the external service
        if path.startswith("/discord/brain"):
            from apex.integrations.discord_brain import get_discord_brain, DiscordBrainConfig
            brain = get_discord_brain()
            if path.endswith("/stats"):
                return brain.get_brain_stats()
            if path.endswith("/config"):
                return DiscordBrainConfig().__dict__

        from apex.integrations.discord_bot import DiscordTradeStore
        store = DiscordTradeStore()
        if path.startswith("/discord/trades/open"):
            return store.get_open_trades()
        if path.startswith("/discord/trades"):
            limit = int((params or {}).get("limit", 50))
            return store.get_all_trades(limit)
        if path.startswith("/discord/stats"):
            return store.get_trade_stats()
    except Exception as e:
        return {"error": f"legacy discord integration error: {e}"}


# Risk Engine endpoint
@app.get("/risk/summary")
def risk_summary():
    from apex.risk.risk_engine import get_risk_engine, PortfolioState
    engine = get_risk_engine()
    state = PortfolioState(
        equity=cache._account.get("equity", 0),
        peak_equity=cache._account.get("equity", 0),
        daily_pl=cache._account.get("daily_pl", 0),
        daily_pl_pct=cache._account.get("daily_pl_pct", 0),
        positions=cache._positions,
    )
    return engine.get_risk_summary(state)

# Performance Analytics endpoint
@app.get("/analytics/performance")
def performance_analytics():
    from apex.analytics.performance import get_performance_analyzer
    analyzer = get_performance_analyzer()
    metrics = analyzer.calculate_metrics()
    return {
        "total_return_pct": metrics.total_return_pct,
        "sharpe_ratio": metrics.sharpe_ratio,
        "sortino_ratio": metrics.sortino_ratio,
        "max_drawdown_pct": metrics.max_drawdown_pct,
        "win_rate": metrics.win_rate,
        "profit_factor": metrics.profit_factor,
        "total_trades": metrics.total_trades,
        "by_source": metrics.by_source,
        "by_symbol": metrics.by_symbol,
    }

# Signal Quality endpoint
@app.get("/analytics/signal-quality")
def signal_quality():
    from apex.analytics.signal_quality import get_signal_tracker
    tracker = get_signal_tracker()
    return {
        "by_source": tracker.get_source_stats(),
        "by_conviction": tracker.get_conviction_accuracy(),
    }

# Discord Brain endpoint
@app.get("/discord/brain/stats")
def discord_brain_stats():
    """Get Discord brain statistics and recent evaluations."""
    # Proxy to external Discord service (preferred) or fall back to local integration
    return _discord_proxy_get("/discord/brain/stats")

@app.get("/discord/brain/config")
def discord_brain_config():
    """Get Discord brain configuration."""
    return _discord_proxy_get("/discord/brain/config")

# Discord Integration Endpoints
@app.get("/discord/trades")
def get_discord_trades(limit: int = 50):
    """Get all Discord-originated trades."""
    return _discord_proxy_get("/discord/trades", params={"limit": limit})

@app.get("/discord/trades/open")
def get_discord_open_trades():
    """Get open Discord trades."""
    return _discord_proxy_get("/discord/trades/open")

@app.get("/discord/stats")
def get_discord_stats():
    """Get Discord trade statistics."""
    return _discord_proxy_get("/discord/stats")
