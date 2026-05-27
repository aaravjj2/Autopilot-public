"""Kalshi scratch / auto-reversal API logic (Week 7 Day 2)."""

from __future__ import annotations

from typing import Any


def submit_scratch_close(
    ticker: str,
    *,
    side: str = "yes",
    size: int = 10,
    limit_price: float | None = None,
) -> dict[str, Any]:
    """Paper scratch — limit close on Kalshi leg."""
    return {
        "status": "paper_scratch",
        "ticker": ticker,
        "side": side,
        "size": size,
        "limit_price": limit_price,
        "order_id": f"scratch-{ticker}-{side}",
    }
