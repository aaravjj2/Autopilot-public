from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI

_MARKET_BACKEND = Path(__file__).resolve().parent


def ensure_marketplace_path() -> None:
    backend = str(_MARKET_BACKEND)
    if backend not in sys.path:
        sys.path.insert(0, backend)
    repo_src = str(_MARKET_BACKEND.parent.parent / "src")
    if repo_src not in sys.path:
        sys.path.insert(0, repo_src)


def register_marketplace(app: FastAPI) -> None:
    """Mount copy-trading marketplace routes on the unified APEX backend."""
    ensure_marketplace_path()
    from marketplace_routes import router

    app.include_router(router)


def marketplace_health() -> dict[str, Any]:
    """Marketplace health payload (portfolio refresh logs + Alpaca ping)."""
    ensure_marketplace_path()
    from alpaca_client import AlpacaClient
    from db import RefreshLog, get_session_sync
    from sqlmodel import select

    alpaca = AlpacaClient()
    ping = alpaca.ping()
    with get_session_sync() as session:
        logs = sorted(
            session.exec(select(RefreshLog)).all(),
            key=lambda row: row.ran_at,
            reverse=True,
        )[:20]
    last_by_portfolio: dict[str, str] = {}
    for row in logs:
        if row.portfolio_id and row.portfolio_id not in last_by_portfolio:
            last_by_portfolio[row.portfolio_id] = row.ran_at.isoformat()
    return {
        "alpaca": ping,
        "last_refresh": last_by_portfolio,
        "timestamp": datetime.now().isoformat(),
    }
