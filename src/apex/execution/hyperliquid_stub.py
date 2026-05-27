"""Hyperliquid / dYdX synthetic hedge stub (Week 7 Day 3)."""

from __future__ import annotations

from typing import Any


def open_perp_hedge(
    symbol: str,
    notional_usd: float,
    *,
    side: str = "short",
) -> dict[str, Any]:
    return {
        "venue": "hyperliquid",
        "symbol": symbol,
        "side": side,
        "notional_usd": notional_usd,
        "status": "paper_filled",
        "order_id": f"hl-{symbol}-{side}",
    }
