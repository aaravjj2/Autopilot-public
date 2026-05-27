"""Maker-taker fee arb — post-only limit stubs (Week 2 Day 4)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PostOnlyOrder:
    venue: str
    ticker: str
    side: str
    price: float
    size: float


def post_only_limits(
    kalshi_ask: float,
    poly_ask: float,
    *,
    tick: float = 0.01,
) -> list[PostOnlyOrder]:
    """Generate post-only bids one tick inside best ask (paper)."""
    return [
        PostOnlyOrder("KALSHI", "", "YES", max(kalshi_ask - tick, tick), 100),
        PostOnlyOrder("POLYMARKET", "", "NO", max(poly_ask - tick, tick), 100),
    ]
