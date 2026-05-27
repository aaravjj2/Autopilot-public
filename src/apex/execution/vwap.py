"""VWAP across L2 orderbook levels (Week 2 Day 2)."""

from __future__ import annotations

from typing import Any, Sequence


def vwap_for_size(
    levels: Sequence[tuple[float, float]],
    target_size: float,
) -> tuple[float | None, int]:
    """
    VWAP = sum(price * vol) / sum(vol) for levels needed to fill target_size.
    Returns (vwap, levels_used). None if insufficient depth.
    """
    if target_size <= 0 or not levels:
        return None, 0
    filled = 0.0
    cost = 0.0
    used = 0
    for price, vol in levels:
        take = min(vol, target_size - filled)
        if take <= 0:
            break
        cost += price * take
        filled += take
        used += 1
        if filled >= target_size - 1e-9:
            break
    if filled < target_size - 1e-9:
        return None, used
    return cost / filled, used


def vwap_from_book(
    book: dict[str, Any],
    side: str,
    target_size: float,
    *,
    max_levels: int = 5,
) -> tuple[float | None, int]:
    """Compute VWAP from Kalshi-style yes/no ladder."""
    ladder = book.get(side) or []
    pairs: list[tuple[float, float]] = []
    for row in ladder[:max_levels]:
        if isinstance(row, (list, tuple)) and len(row) >= 2:
            pairs.append((float(row[0]), float(row[1])))
    return vwap_for_size(pairs, target_size)


def liquidity_gate_ok(
    book: dict[str, Any],
    target_size: float,
    *,
    multiplier: float = 3.0,
    max_levels: int = 5,
) -> bool:
    """M07: reject if top-5 depth < multiplier * target_size (Week 2 Day 3)."""
    total = 0.0
    for side in ("yes", "no"):
        ladder = book.get(side) or []
        for row in ladder[:max_levels]:
            if isinstance(row, (list, tuple)) and len(row) >= 2:
                total += float(row[1])
    return total >= multiplier * target_size
