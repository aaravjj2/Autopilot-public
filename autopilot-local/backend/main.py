from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent / "src"))
from apex.integrations.thesis_service import router as thesis_router
from marketplace_routes import router as marketplace_router
from marketplace_integration import marketplace_health

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)


# Global queue for SQLite writes (arb stream → APEX audit store)
arb_write_queue: asyncio.Queue = asyncio.Queue()


@asynccontextmanager
async def lifespan(app: FastAPI):
    from marketplace_lifecycle import marketplace_lifespan

    async with marketplace_lifespan(enable_arb_worker=True):
        yield


app = FastAPI(title="Autopilot Local API", version="1.0.0", lifespan=lifespan)

def _cors_origins() -> list[str]:
    from apex.core.config import get_settings

    s = get_settings()
    origins = [o.strip() for o in (s.cors_origins or "").split(",") if o.strip()]
    return origins or ["http://localhost:3000", "http://127.0.0.1:3000"]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(thesis_router)

try:
    from agent.gateway import router as agent_router

    app.include_router(agent_router)
except ImportError:
    pass

app.include_router(marketplace_router)


@app.get("/api/demo/status")
def demo_status_local():
    from apex.core.config import get_settings
    from apex.repositories.sqlite_store import SQLiteStore

    s = get_settings()
    store = SQLiteStore(s.sqlite_path)
    return {
        "demo_mode": s.demo_mode,
        "paper_only": bool(s.alpaca_paper_trade),
        "arb_opportunities": len(store.list_arb_opportunities(limit=50)),
    }


@app.get("/api/opportunities")
def get_opportunities():
    from apex.core.config import get_settings
    from apex.repositories.sqlite_store import SQLiteStore
    settings = get_settings()
    store = SQLiteStore(settings.sqlite_path)
    return store.list_arb_opportunities()

@app.get("/api/arb/summary")
def get_arb_summary():
    from apex.core.config import get_settings
    from apex.repositories.sqlite_store import SQLiteStore
    settings = get_settings()
    store = SQLiteStore(settings.sqlite_path)
    
    # Simple summary stats
    all_opps = store.list_arb_opportunities()
    resolved = store.get_resolved_arb_opportunities(limit=1000)
    
    wins = len([o for o in resolved if (o.get("pnl") or 0) > 0])
    total = len(resolved)
    win_rate = (wins / total) if total > 0 else 0.0
    
    return {
        "active_opportunities": len(all_opps),
        "resolved_opportunities": total,
        "win_rate": win_rate
    }

@app.websocket("/api/arb/stream")
async def stream_opportunities(websocket: WebSocket):
    await websocket.accept()
    from apex.core.config import get_settings
    from apex.repositories.sqlite_store import SQLiteStore
    from apex.services.arb_engine import ArbEngine
    from dataclasses import asdict
    import asyncio
    
    settings = get_settings()
    store = SQLiteStore(settings.sqlite_path)
    engine = ArbEngine(settings=settings, store=store)
    
    try:
        while True:
            # Run scan in a separate thread since it contains synchronous HTTP requests
            opps = await asyncio.to_thread(engine.scan)
            
            # Send to SQLite worker queue
            if opps:
                await arb_write_queue.put(opps)
            
            # Send current opportunities
            payload = {"type": "data", "opportunities": [asdict(o) for o in opps]}
            await websocket.send_json(payload)
            
            # Dynamic sleep based on max edge found
            max_edge = max([o.net_edge for o in opps]) if opps else 0
            if max_edge > 0.03:
                sleep_sec = 2  # hyper-aggressive tracking (3%+ edge)
            elif max_edge > 0.01:
                sleep_sec = 5  # active tracking (1%+ edge)
            else:
                sleep_sec = 10 # standard polling
                
            # Send status update so frontend knows the polling rate
            await websocket.send_json({"type": "status", "polling_rate_sec": sleep_sec, "max_edge": max_edge})
            
            await asyncio.sleep(sleep_sec)
    except WebSocketDisconnect:
        LOGGER.info("WebSocket disconnected from /api/arb/stream")
    except Exception as e:
        LOGGER.error("WebSocket stream error: %s", e)
        await websocket.close()


@app.post("/api/arb/{arb_id}/paper-trade")
async def paper_trade_arb(arb_id: str):
    from apex.core.config import get_settings
    from apex.repositories.sqlite_store import SQLiteStore
    from apex.domain.models import ArbOpportunity, AuditEvent
    from apex.domain.enums import EventType

    settings = get_settings()
    store = SQLiteStore(settings.sqlite_path)
    opp_dict = store.get_arb_opportunity(arb_id)
    if not opp_dict:
        raise HTTPException(status_code=404, detail="Arb opportunity not found")

    opp = ArbOpportunity(**{k: v for k, v in opp_dict.items() if k != "settlement_flags"})
    opp.settlement_flags = json.loads(opp_dict.get("settlement_flags", "[]"))

    if settings.demo_mode or arb_id == "demo-reject-demo":
        if arb_id == "demo-reject-demo" or (opp.net_edge or 0) < 0.01:
            raise HTTPException(status_code=400, detail="Risk failed: M07 (demo)")
        kid = f"demo-kalshi-{arb_id[:8]}"
        pid = f"demo-poly-{arb_id[:8]}"
        store.append_event(
            AuditEvent(
                event_type=EventType.ARB_PAPER_SUBMITTED,
                symbol=opp.kalshi_ticker,
                order_id=kid,
                raw_payload={"kalshi_order_id": kid, "poly_order_id": pid, "demo_mode": True},
            )
        )
        return {"status": "ok", "kalshi_order_id": kid, "poly_order_id": pid, "demo_mode": True}

    from apex.main import build_engine

    engine = build_engine()
    kalshi_id, poly_id = await engine.execution.submit_arb_paper_orders(opp, stake_usd=50.0)
    if not kalshi_id:
        raise HTTPException(status_code=400, detail="Paper trade rejected by risk checks")

    return {"status": "ok", "kalshi_order_id": kalshi_id, "poly_order_id": poly_id}


@app.post("/api/arb/{arb_id}/thesis/chat")
async def thesis_chat(arb_id: str, payload: dict):
    from fastapi import HTTPException
    from apex.core.config import get_settings
    from apex.repositories.sqlite_store import SQLiteStore
    from apex.services.thesis_client import ThesisClient

    settings = get_settings()
    store = SQLiteStore(settings.sqlite_path)
    opp_dict = store.get_arb_opportunity(arb_id)
    if not opp_dict:
        raise HTTPException(status_code=404, detail="Arb opportunity not found")

    # Extract user message; ignore history for now
    message = payload.get("message", "")
    # Build a simple prompt combining opportunity details and user message
    prompt = f"Opportunity: {opp_dict.get('question', '')}\nUser: {message}\nProvide a concise reply."

    client = ThesisClient()
    # Stream tokens and concatenate them
    reply_parts = []
    async for token in client.stream_thesis(prompt):
        reply_parts.append(token)
    reply = "".join(reply_parts)
    return {"reply": reply}



@app.get("/api/arb/backtest")
async def get_backtest(lookback_days: int = 90):
    from apex.services.backtest_engine import BacktestEngine
    from apex.core.config import get_settings
    from apex.repositories.sqlite_store import SQLiteStore
    
    settings = get_settings()
    store    = SQLiteStore(settings.sqlite_path)
    engine   = BacktestEngine(settings=settings, store=store)
    result   = engine.run(lookback_days=lookback_days)
    return {
        "n_trades":      result.n_trades,
        "win_rate":      result.win_rate,
        "sharpe":        result.sharpe,
        "total_pnl":     result.total_pnl,
        "avg_net_edge":  result.avg_net_edge,
        "avg_hold_days": result.avg_hold_days,
        "edge_per_day":  result.edge_per_day,
        "annualized_roc": result.annualized_roc,
        "slippage_adjusted_sharpe": result.slippage_adjusted_sharpe,
        "per_category_stats": result.per_category_stats,
    }


@app.get("/api/health")
def health() -> dict[str, Any]:
    return marketplace_health()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
