"""Smart Order Router (Week 2 Day 5)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SorLeg:
    venue: str
    side: str
    size_usd: float
    limit_price: float
    gas_strategy: str | None = None


@dataclass
class SorRequest:
    arb_id: str
    strategy: str = "AGGRESSIVE_TAKER"
    max_slippage_bps: int = 25
    legs: list[SorLeg] = field(default_factory=list)
    fallback: dict[str, Any] = field(default_factory=dict)


def split_notional_across_legs(
    total_usd: float,
    venues: list[str],
) -> list[SorLeg]:
    """Distribute notional evenly across venues (paper mode)."""
    if not venues:
        return []
    each = round(total_usd / len(venues), 2)
    return [
        SorLeg(venue=v, side="YES" if v == "KALSHI" else "NO", size_usd=each, limit_price=0.5)
        for v in venues
    ]


def build_sor_from_payload(payload: dict[str, Any]) -> SorRequest:
    legs = [
        SorLeg(
            venue=str(leg.get("venue", "")),
            side=str(leg.get("side", "")),
            size_usd=float(leg.get("size_usd", 0)),
            limit_price=float(leg.get("limit_price", 0)),
            gas_strategy=leg.get("gas_strategy"),
        )
        for leg in payload.get("legs", [])
    ]
    return SorRequest(
        arb_id=str(payload.get("arb_id", "")),
        strategy=str(payload.get("strategy", "AGGRESSIVE_TAKER")),
        max_slippage_bps=int(payload.get("max_slippage_bps", 25)),
        legs=legs,
        fallback=dict(payload.get("fallback") or {}),
    )


def execute_sor_paper(req: SorRequest) -> dict[str, Any]:
    """Paper execution — VWAP-aware routing plan (Phase 3)."""
    from apex.cache.orderbook_l2 import read_orderbook
    from apex.execution.vwap import vwap_from_book

    leg_results = []
    total_usd = sum(leg.size_usd for leg in req.legs)
    for leg in req.legs:
        venue = leg.venue.upper()
        ticker = req.arb_id if venue == "POLY" else leg.venue
        book = read_orderbook(venue, ticker) or {}
        side = "yes" if leg.side.upper() == "YES" else "no"
        vwap, levels = vwap_from_book(book, side, leg.size_usd) if book else (None, 0)
        slippage_bps = 0
        if vwap and leg.limit_price:
            slippage_bps = int(abs(vwap - leg.limit_price) / max(leg.limit_price, 1e-6) * 10000)
        ok = slippage_bps <= req.max_slippage_bps
        leg_results.append({
            "venue": leg.venue,
            "side": leg.side,
            "size_usd": leg.size_usd,
            "limit_price": leg.limit_price,
            "vwap": vwap,
            "levels_used": levels,
            "slippage_bps": slippage_bps,
            "status": "simulated_fill" if ok else "rejected_slippage",
        })

    return {
        "status": "paper_routed",
        "arb_id": req.arb_id,
        "strategy": req.strategy,
        "total_notional_usd": total_usd,
        "legs": leg_results,
        "all_passed": all(leg["status"] == "simulated_fill" for leg in leg_results),
    }
