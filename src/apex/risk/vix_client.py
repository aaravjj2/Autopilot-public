"""CBOE VIX fetch for volatility dampener (Week 6 Day 2)."""

from __future__ import annotations

import logging
import time
from typing import Optional

LOGGER = logging.getLogger(__name__)

_cache: dict[str, float | int] = {"value": 20.0, "ts": 0.0}
_CACHE_TTL_SEC = 300


def fetch_vix_yfinance() -> Optional[float]:
    try:
        import yfinance as yf

        ticker = yf.Ticker("^VIX")
        hist = ticker.history(period="1d")
        if hist is not None and not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception as exc:
        LOGGER.warning("VIX yfinance fetch failed: %s", exc)
    return None


def get_vix(force_refresh: bool = False) -> float:
    """Return latest VIX with 5-minute cache; fallback 20."""
    now = time.time()
    if not force_refresh and now - float(_cache["ts"]) < _CACHE_TTL_SEC:
        return float(_cache["value"])

    vix = fetch_vix_yfinance()
    if vix is None:
        try:
            import httpx

            # CBOE delayed index (public CSV-style endpoint may vary)
            resp = httpx.get(
                "https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv",
                timeout=15,
                follow_redirects=True,
            )
            if resp.status_code == 200:
                lines = resp.text.strip().splitlines()
                if len(lines) > 1:
                    last = lines[-1].split(",")
                    if len(last) >= 5:
                        vix = float(last[4])
        except Exception as exc:
            LOGGER.debug("VIX CBOE CSV fallback failed: %s", exc)

    if vix is not None and vix > 0:
        _cache["value"] = vix
        _cache["ts"] = now
        return vix

    return float(_cache["value"])
