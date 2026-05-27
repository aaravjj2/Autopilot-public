"""Scale one trade to N follower accounts (Week 10 Day 3)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class CopyLeg:
    account_id: str
    size_usd: float
    status: str = "pending"


def scale_trade(
    master_leg: dict[str, Any],
    follower_accounts: list[str],
    *,
    scale_factor: float = 1.0,
) -> list[CopyLeg]:
    base = float(master_leg.get("size_usd") or 50.0) * scale_factor
    return [
        CopyLeg(account_id=aid, size_usd=round(base, 2), status="paper_queued")
        for aid in follower_accounts
    ]
