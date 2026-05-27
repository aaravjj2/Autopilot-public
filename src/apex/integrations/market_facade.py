"""Unified Alpaca + yfinance market data for terminal API."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from apex.core.config import Settings, get_settings
from apex.core.logging import get_logger
from apex.integrations.alpaca_adapter import AlpacaDirectIntegration
from apex.integrations.hub import get_integration_hub
from apex.integrations.market_data import YFinanceMarketDataClient, YFinanceOptionsDataClient

LOGGER = get_logger(__name__)

_TIMEFRAME_MAP = {
    "1m": ("1Min", 5),
    "5m": ("5Min", 10),
    "15m": ("15Min", 20),
    "1h": ("1Hour", 60),
    "4h": ("4Hour", 120),
    "1d": ("1Day", 252),
    "1w": ("1Day", 60),
    "1wk": ("1Day", 60),
}


def get_alpaca_client(settings: Settings | None = None) -> AlpacaDirectIntegration:
    settings = settings or get_settings()
    hub = get_integration_hub()
    hub.initialize()
    if hub.alpaca_direct is not None:
        return hub.alpaca_direct
    return AlpacaDirectIntegration(
        api_key=settings.alpaca_api_key,
        secret_key=settings.alpaca_secret_key,
        base_url=settings.alpaca_base_url,
        paper_trade=settings.alpaca_paper_trade,
    )


def probe_yfinance() -> tuple[bool, str]:
    try:
        import yfinance as yf

        hist = yf.Ticker("SPY").history(period="5d", interval="1d")
        if hist is None or hist.empty:
            return False, "yfinance returned no SPY data"
        return True, "ok"
    except Exception as exc:
        return False, str(exc)


def probe_market_feeds(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    alpaca = get_alpaca_client(settings)
    yf_ok, yf_detail = probe_yfinance()
    return {
        "alpaca": {
            "available": alpaca.available,
            "detail": "connected" if alpaca.available else "not configured",
        },
        "yfinance": {"available": yf_ok, "detail": yf_detail},
    }


def _alpaca_bars_to_chart(symbol: str, raw: dict[str, Any]) -> list[dict[str, Any]]:
    bars = (raw.get("bars") or {}).get(symbol.upper()) or []
    out: list[dict[str, Any]] = []
    for bar in bars:
        ts = bar.get("t") or bar.get("timestamp")
        if not ts:
            continue
        if isinstance(ts, str):
            ts_ms = int(datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp() * 1000)
        else:
            ts_ms = int(ts)
        out.append({
            "time": ts_ms,
            "open": float(bar.get("o", bar.get("open", 0))),
            "high": float(bar.get("h", bar.get("high", 0))),
            "low": float(bar.get("l", bar.get("low", 0))),
            "close": float(bar.get("c", bar.get("close", 0))),
            "volume": float(bar.get("v", bar.get("volume", 0))),
        })
    return out


def get_chart_bars(symbol: str, timeframe: str = "1D") -> tuple[list[dict[str, Any]], str]:
    """Returns (bars, source) — Alpaca when configured for intraday, else yfinance daily."""
    settings = get_settings()
    sym = symbol.upper()
    tf = timeframe.lower().strip()
    alpaca_tf, lookback = _TIMEFRAME_MAP.get(tf, ("1Day", 252))
    use_alpaca = tf in {"1m", "5m", "15m", "1h", "4h"}

    if use_alpaca:
        client = get_alpaca_client(settings)
        if client.available:
            raw = client.get_bars([sym], timeframe=alpaca_tf, limit=min(lookback * 78, 1000))
            formatted = _alpaca_bars_to_chart(sym, raw if isinstance(raw, dict) else {})
            if formatted:
                return formatted, "alpaca"

    yf = YFinanceMarketDataClient()
    daily_lookback = lookback if alpaca_tf == "1Day" else 252
    bars = yf.get_daily_bars(sym, lookback_days=daily_lookback)
    out: list[dict[str, Any]] = []
    for bar in bars:
        t = bar.get("time") or bar.get("date")
        if t is None:
            continue
        if hasattr(t, "timestamp"):
            ts_ms = int(t.timestamp() * 1000)
        elif isinstance(t, (int, float)):
            ts_ms = int(t)
        else:
            ts_ms = int(datetime.fromisoformat(str(t)).replace(tzinfo=timezone.utc).timestamp() * 1000)
        out.append({
            "time": ts_ms,
            "open": float(bar.get("open", 0)),
            "high": float(bar.get("high", 0)),
            "low": float(bar.get("low", 0)),
            "close": float(bar.get("close", 0)),
            "volume": float(bar.get("volume", 0)),
        })
    return out, "yfinance"


def get_options_chain(symbol: str) -> dict[str, Any]:
    return YFinanceOptionsDataClient().get_option_chain(symbol.upper())


def record_equity_snapshot(store: Any, account: dict[str, Any]) -> None:
    if not account or account.get("error"):
        return
    equity = float(account.get("equity") or account.get("portfolio_value") or 0)
    if equity <= 0:
        return
    try:
        positions_val = sum(float(p.get("market_value") or 0) for p in (account.get("positions") or []))
    except Exception:
        positions_val = 0.0
    ts = datetime.now(timezone.utc).isoformat()
    cash = float(account.get("cash") or account.get("buying_power") or 0)
    store.add_equity_point(ts, equity, cash=cash, positions_value=positions_val)
