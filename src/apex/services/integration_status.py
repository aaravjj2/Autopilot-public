"""Live integration status for the trading terminal API."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

from apex.core.config import Settings, get_settings
from apex.integrations.alpaca_adapter import AlpacaDirectIntegration
from apex.integrations.repo_registry import IntegrationRegistry

_REPO_ROOT = Path(__file__).resolve().parents[3]
_EXTERNAL = _REPO_ROOT / "external"

_BUNDLED: dict[str, str] = {
    "tradingagents": "TradingAgents",
    "dexter": "dexter",
    "polymarket": "PolyMarket-MCP",
    "polymarket_mcp": "polymarket-mcp-server",
}

_status_cache: dict[str, Any] | None = None
_status_cache_at: float = 0.0
_CACHE_TTL_SEC = 30.0


def _resolve_path(settings: Settings, attr: str, bundled_key: str) -> str:
    raw = (getattr(settings, attr, "") or "").strip()
    if raw:
        p = Path(raw).expanduser()
        if not p.is_absolute():
            p = (_REPO_ROOT / p).resolve()
        return str(p)
    name = _BUNDLED.get(bundled_key, "")
    if name:
        candidate = _EXTERNAL / name
        if candidate.is_dir():
            return str(candidate.resolve())
    return ""


def _probe_yfinance() -> tuple[bool, str]:
    try:
        import yfinance as yf

        hist = yf.Ticker("SPY").history(period="5d", interval="1d")
        if hist is None or hist.empty:
            return False, "yfinance returned no data for SPY"
        return True, "market data OK"
    except Exception as exc:
        return False, str(exc)


def _probe_alpaca(settings: Settings) -> tuple[bool, str]:
    client = AlpacaDirectIntegration(
        api_key=settings.alpaca_api_key,
        secret_key=settings.alpaca_secret_key,
        base_url=settings.alpaca_base_url,
    )
    if not client.available:
        return False, "Alpaca API keys not configured"
    account = client.get_account()
    if account.get("error"):
        return False, str(account.get("error", "account error"))[:200]
    if (account.get("status") or "").lower() in {"error", "exception"}:
        return False, str(account.get("status"))
    return True, f"account {account.get('status', 'ok')}"


def build_integrations_status(*, force: bool = False) -> dict[str, Any]:
    global _status_cache, _status_cache_at
    now = time.monotonic()
    if (
        not force
        and _status_cache is not None
        and (now - _status_cache_at) < _CACHE_TTL_SEC
    ):
        return _status_cache

    settings = get_settings()
    from apex.integrations.hub import get_integration_hub

    hub = get_integration_hub()
    registry = IntegrationRegistry(settings)

    yfinance_ok, yfinance_detail = _probe_yfinance()
    alpaca_ok, alpaca_detail = _probe_alpaca(settings)

    ta_path = _resolve_path(settings, "tradingagents_repo_path", "tradingagents")
    dex_path = _resolve_path(settings, "dexter_repo_path", "dexter")
    pm_path = _resolve_path(settings, "polymarket_repo_path", "polymarket") or _resolve_path(
        settings, "polymarket_mcp_path", "polymarket_mcp"
    )

    llm_ok = hub.has_groq()
    llm_provider = (settings.llm_provider or "ollama").lower()

    services: dict[str, dict[str, Any]] = {
        "alpaca": {
            "connected": alpaca_ok,
            "detail": alpaca_detail,
            "path": settings.alpaca_base_url,
        },
        "yfinance": {
            "connected": yfinance_ok,
            "detail": yfinance_detail,
        },
        "polymarket": {
            "connected": hub.has_polymarket(),
            "detail": pm_path or "not configured",
            "path": pm_path,
        },
        "tradingagents": {
            "connected": hub.has_trading_agents(),
            "detail": ta_path or "not configured",
            "path": ta_path,
        },
        "dexter": {
            "connected": hub.has_dexter(),
            "detail": dex_path or "not configured",
            "path": dex_path,
        },
        "llm": {
            "connected": llm_ok,
            "detail": f"{llm_provider} ({'ready' if llm_ok else 'unavailable'})",
            "provider": llm_provider,
        },
        "discord": {
            "connected": bool(os.getenv("DISCORD_USER_TOKEN", "").strip()),
            "detail": "token configured" if os.getenv("DISCORD_USER_TOKEN") else "no token",
        },
    }

    payload: dict[str, Any] = {
        "timestamp": time.time(),
        "alpaca": services["alpaca"]["connected"],
        "yfinance": services["yfinance"]["connected"],
        "polymarket": services["polymarket"]["connected"],
        "tradingagents": services["tradingagents"]["connected"],
        "dexter": services["dexter"]["connected"],
        "llm": services["llm"]["connected"],
        "discord": services["discord"]["connected"],
        "services": services,
        "repos": registry.repo_status(),
        "credentials": registry.credential_status(),
    }

    _status_cache = payload
    _status_cache_at = now
    return payload
