"""Cross-asset event mappings (Week 3 Day 3)."""

from __future__ import annotations

CROSS_ASSET_MAP: dict[str, list[str]] = {
    "SPACEX_LAUNCH": ["TSLA", "RKLB"],
    "FED_RATE": ["SPY", "TLT", "SHY"],
    "BTC_ETF": ["BTC", "COIN", "MSTR"],
}


def hedge_tickers_for_event(event_key: str) -> list[str]:
    return CROSS_ASSET_MAP.get(event_key.upper(), [])
