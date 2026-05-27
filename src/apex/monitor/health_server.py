from __future__ import annotations

import sqlite3

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route


def _ready(_request: Request) -> JSONResponse:
    from apex.core.config import get_settings

    s = get_settings()
    try:
        conn = sqlite3.connect(str(s.sqlite_path))
        conn.execute("SELECT 1").fetchone()
        conn.close()
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"status": "not_ready", "error": str(exc)}, status_code=503)
    return JSONResponse({"status": "ready", "sqlite_path": str(s.sqlite_path)})


def healthz_handler(request: Request) -> JSONResponse:
    from apex.core.config import get_settings

    s = get_settings()
    deep = request.query_params.get("deep") == "1"
    try:
        conn = sqlite3.connect(str(s.sqlite_path))
        conn.execute("SELECT 1").fetchone()
        conn.close()
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"status": "error", "sqlite": False, "error": str(exc)}, status_code=503)

    body: dict = {"status": "ok", "sqlite": True}
    if deep:
        from apex.dashboard.health import _probe_llm_route

        try:
            row = _probe_llm_route(s)
            body["probes"] = [{"name": "llm", "status": row.status, "detail": row.detail}]
        except Exception as exc:  # noqa: BLE001
            body["probes_error"] = str(exc)
        # Enrich with position + P&L summary
        try:
            from apex.integrations.hub import get_integration_hub
            hub = get_integration_hub()
            if hub and hub.has_alpaca():
                acct = hub.alpaca_direct.get_account()
                equity = float(acct.get("equity", 0) or 0)
                bp = float(acct.get("buying_power", 0) or 0)
                options_bp = float(acct.get("options_buying_power", 0) or 0)
                positions = hub.alpaca_direct.get_positions()
                open_positions = len(positions)
                total_unrealized_pl = sum(float(p.get("unrealized_pl", 0) or 0) for p in positions)
                body["alpaca"] = {
                    "equity": equity,
                    "buying_power": bp,
                    "options_buying_power": options_bp,
                    "open_positions": open_positions,
                    "unrealized_pl": round(total_unrealized_pl, 2),
                }
        except Exception as exc:
            body["alpaca_error"] = str(exc)
        # Recent trade stats
        try:
            cur = sqlite3.connect(str(s.sqlite_path)).cursor()
            cur.execute("SELECT COUNT(*), COALESCE(SUM(pnl),0) FROM completed_trades WHERE exit_time >= date('now')")
            row = cur.fetchone()
            body["today"] = {"closed_trades": row[0], "pnl": round(row[1] or 0, 2)} if row else {}
            cur.connection.close()
        except Exception:
            pass
    return JSONResponse(body)


app = Starlette(
    routes=[
        Route("/ready", endpoint=_ready, methods=["GET"]),
        Route("/healthz", endpoint=healthz_handler, methods=["GET"]),
    ]
)
