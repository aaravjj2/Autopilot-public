from __future__ import annotations

import json
import uuid
from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, HTTPException

from agent.arize_bridge import get_arize_bridge
from apex.core.config import get_settings
from apex.repositories.sqlite_store import SQLiteStore
from apex.services.arb_engine import ArbEngine
from apex.services.backtest_engine import BacktestEngine

router = APIRouter(prefix="/api/agent", tags=["agent"])

MISSIONS: dict[str, dict[str, Any]] = {
    "morning_arb_briefing": {
        "title": "Morning arb briefing",
        "steps": ["scan_arbitrage", "rank top 3", "explain match confidence"],
        "prompt": (
            "Run a morning arbitrage briefing: scan all opportunities, pick the top 3 by "
            "net_edge, and explain settlement match scores and risks for each."
        ),
    },
    "governed_paper_execution": {
        "title": "Governed paper execution",
        "steps": ["select opportunity", "explain_risk_gates", "paper_trade_arb"],
        "prompt": (
            "Select the highest net-edge opportunity that passes risk gates, explain which "
            "gates were evaluated, then submit a paper trade or explain rejection."
        ),
    },
    "incident_post_mortem": {
        "title": "Incident post-mortem",
        "steps": ["get_audit_tail", "summarize failure", "suggest tweak"],
        "prompt": (
            "Pull recent audit events for failed risk checks, summarize root cause, and "
            "suggest one parameter tweak for safer paper trading."
        ),
    },
}


def _store() -> SQLiteStore:
    s = get_settings()
    return SQLiteStore(s.sqlite_path)


@router.get("/missions")
def list_missions() -> dict[str, Any]:
    return {"missions": MISSIONS, "track": "Arize", "stack": "Gemini + Agent Builder + APEX MCP"}


@router.get("/tools")
def list_tools() -> list[dict[str, str]]:
    return [
        {"name": "scan_arbitrage", "description": "Scan Kalshi × Polymarket for arb opportunities"},
        {"name": "get_opportunity", "description": "Fetch one opportunity by id"},
        {"name": "explain_risk_gates", "description": "List 14-check risk gate status for an arb"},
        {"name": "paper_trade_arb", "description": "Submit governed paper dual-leg trade"},
        {"name": "get_audit_tail", "description": "Recent audit log events"},
        {"name": "backtest_summary", "description": "Arb backtest metrics"},
    ]


@router.post("/run/{mission_id}")
async def run_mission(mission_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if mission_id not in MISSIONS:
        raise HTTPException(status_code=404, detail=f"Unknown mission: {mission_id}")

    settings = get_settings()
    store = _store()
    arize = get_arize_bridge()
    trace_id = uuid.uuid4().hex
    body = payload or {}
    arb_id = body.get("arb_id")

    steps_out: list[dict[str, Any]] = []

    with arize.span("mission.start", trace_id=trace_id, attributes={"mission": mission_id}):
        pass

    if mission_id == "morning_arb_briefing":
        with arize.span("tool.scan_arbitrage", trace_id=trace_id):
            engine = ArbEngine(settings=settings, store=store)
            opps = engine.scan()
            ranked = sorted(opps, key=lambda o: -o.net_edge)[:3]
            steps_out.append(
                {
                    "tool": "scan_arbitrage",
                    "count": len(opps),
                    "top3": [
                        {
                            "id": o.id,
                            "ticker": o.kalshi_ticker,
                            "net_edge": o.net_edge,
                            "match_score": o.settlement_match_score,
                        }
                        for o in ranked
                    ],
                }
            )

    elif mission_id == "governed_paper_execution":
        with arize.span("tool.select_opportunity", trace_id=trace_id):
            rows = store.list_arb_opportunities(limit=20)
            pick = None
            for row in sorted(rows, key=lambda r: -(r.get("net_edge") or 0)):
                if row.get("id") == "demo-reject-demo":
                    continue
                pick = row
                break
            if not pick and rows:
                pick = rows[0]
            if not pick:
                raise HTTPException(status_code=404, detail="No opportunities")
            arb_id = pick["id"]
            steps_out.append({"tool": "select_opportunity", "arb_id": arb_id})

        with arize.span("tool.explain_risk_gates", trace_id=trace_id, attributes={"arb_id": arb_id}):
            gates = _explain_risk_gates(arb_id, store, settings)
            steps_out.append({"tool": "explain_risk_gates", "gates": gates})

        with arize.span("tool.paper_trade_arb", trace_id=trace_id, attributes={"arb_id": arb_id}):
            trade = await _paper_trade_internal(arb_id, store, settings)
            steps_out.append({"tool": "paper_trade_arb", "result": trade})

    elif mission_id == "incident_post_mortem":
        with arize.span("tool.get_audit_tail", trace_id=trace_id):
            events = store.list_audit_events(limit=30)
            failed = [
                e
                for e in events
                if "FAIL" in str(e.get("event_type", ""))
                or e.get("rejection_reason")
            ]
            steps_out.append(
                {
                    "tool": "get_audit_tail",
                    "failed_count": len(failed),
                    "sample": failed[:5],
                    "recommendation": "Raise arb_min_net_edge or tighten M07 liquidity threshold",
                }
            )

    return {
        "mission_id": mission_id,
        "trace_id": trace_id,
        "arize_trace_url": arize.trace_url(trace_id),
        "steps": steps_out,
        "mission": MISSIONS[mission_id],
    }


@router.post("/tools/scan_arbitrage")
def tool_scan_arbitrage() -> dict[str, Any]:
    settings = get_settings()
    arize = get_arize_bridge()
    trace_id = uuid.uuid4().hex
    with arize.span("scan_arbitrage", trace_id=trace_id):
        engine = ArbEngine(settings=settings, store=_store())
        opps = [asdict(o) for o in engine.scan()]
    return {"trace_id": trace_id, "opportunities": opps, "count": len(opps)}


@router.get("/tools/opportunity/{arb_id}")
def tool_get_opportunity(arb_id: str) -> dict[str, Any]:
    row = _store().get_arb_opportunity(arb_id)
    if not row:
        raise HTTPException(status_code=404, detail="not found")
    return row


@router.get("/tools/risk_gates/{arb_id}")
def tool_risk_gates(arb_id: str) -> dict[str, Any]:
    settings = get_settings()
    return {"arb_id": arb_id, "gates": _explain_risk_gates(arb_id, _store(), settings)}


@router.post("/tools/paper_trade/{arb_id}")
async def tool_paper_trade(arb_id: str) -> dict[str, Any]:
    settings = get_settings()
    return await _paper_trade_internal(arb_id, _store(), settings)


@router.get("/tools/audit_tail")
def tool_audit_tail(limit: int = 40) -> dict[str, Any]:
    events = _store().list_audit_events(limit=limit)
    return {"events": events, "count": len(events)}


@router.get("/tools/backtest")
def tool_backtest(lookback_days: int = 90) -> dict[str, Any]:
    settings = get_settings()
    store = _store()
    result = BacktestEngine(settings=settings, store=store).run(lookback_days=lookback_days)
    return asdict(result)


@router.get("/traces")
def list_traces(limit: int = 30) -> dict[str, Any]:
    return {"spans": get_arize_bridge().recent_spans(limit=limit)}


def _explain_risk_gates(arb_id: str, store: SQLiteStore, settings: Any) -> list[dict[str, Any]]:
    from apex.domain.models import ArbOpportunity
    from apex.layers.l3.risk_checks import RiskCheckEngine

    row = store.get_arb_opportunity(arb_id)
    if not row:
        return [{"gate": "lookup", "passed": False, "reason": "opportunity not found"}]
    opp = ArbOpportunity(**{k: v for k, v in row.items() if k != "settlement_flags"})
    opp.settlement_flags = json.loads(row.get("settlement_flags") or "[]")
    risk = RiskCheckEngine(settings).run_arb_paper(opp, stake_usd=50.0)
    gates = [{"gate": g, "passed": True} for g in risk.passed]
    gates += [{"gate": g, "passed": False} for g in risk.failed]
    if risk.rejection_reason:
        gates.append({"gate": "summary", "passed": False, "reason": risk.rejection_reason})
    return gates


async def _paper_trade_internal(arb_id: str, store: SQLiteStore, settings: Any) -> dict[str, Any]:
    import json

    from apex.domain.enums import EventType
    from apex.domain.models import ArbOpportunity, AuditEvent

    row = store.get_arb_opportunity(arb_id)
    if not row:
        raise HTTPException(status_code=404, detail="Arb opportunity not found")
    opp = ArbOpportunity(**{k: v for k, v in row.items() if k != "settlement_flags"})
    opp.settlement_flags = json.loads(row.get("settlement_flags") or "[]")

    if settings.demo_mode or arb_id == "demo-reject-demo":
        if arb_id == "demo-reject-demo" or (opp.net_edge or 0) < 0.01:
            raise HTTPException(
                status_code=400,
                detail="Risk failed: M07 insufficient liquidity (demo)",
            )
        kid = f"demo-kalshi-{arb_id[:8]}"
        pid = f"demo-poly-{arb_id[:8]}"
        store.append_event(
            AuditEvent(
                event_type=EventType.ARB_PAPER_SUBMITTED,
                symbol=opp.kalshi_ticker,
                order_id=kid,
                raw_payload={"arb_id": arb_id, "kalshi_order_id": kid, "poly_order_id": pid},
            )
        )
        return {"status": "ok", "kalshi_order_id": kid, "poly_order_id": pid, "demo_mode": True}

    from apex.main import build_engine

    engine = build_engine()
    risk = engine.risk_engine.run_arb_paper(opp, stake_usd=50.0)
    if not risk.all_passed:
        raise HTTPException(status_code=400, detail=risk.rejection_reason or str(risk.failed))
    kalshi_id, poly_id = await engine.execution.submit_arb_paper_orders(opp, thesis=None)
    if not kalshi_id:
        raise HTTPException(status_code=400, detail="Paper trade execution failed")
    return {"status": "ok", "kalshi_order_id": kalshi_id, "poly_order_id": poly_id}
