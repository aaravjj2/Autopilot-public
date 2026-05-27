"""DeFi treasury & MEV stubs (Week 5)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class SweepResult:
    deposited_usd: float
    aave_apy: float
    tx_hash: str | None


def sweep_idle_usdc_to_aave(amount_usd: float) -> SweepResult:
    """Paper Aave sweep (Week 5 Day 2)."""
    return SweepResult(deposited_usd=amount_usd, aave_apy=0.042, tx_hash=None)


def route_swap_1inch(from_token: str, to_token: str, amount: float) -> dict[str, Any]:
    """1inch routing stub (Week 5 Day 3)."""
    return {"from": from_token, "to": to_token, "amount": amount, "route": "paper"}


def detect_mev_sandwich(tx_receipt: dict[str, Any]) -> bool:
    """Heuristic MEV detection (Week 5 Day 5)."""
    gas_used = int(tx_receipt.get("gasUsed") or 0)
    return gas_used > 500_000


def treasury_status() -> dict[str, Any]:
    """Aggregated paper treasury status for API/UI."""
    sweep = sweep_idle_usdc_to_aave(0.0)
    route = route_swap_1inch("MATIC", "USDC", 0.0)
    return {
        "aave": {"status": "paper", "apy_pct": round(sweep.aave_apy * 100, 2)},
        "sweep": {"last_sweep_usd": sweep.deposited_usd, "status": "idle"},
        "mev": {
            "status": "clear" if not detect_mev_sandwich({"gasUsed": 100_000}) else "alert",
            "sandwich_detected": detect_mev_sandwich({"gasUsed": 600_000}),
        },
        "oneinch": {"route_available": route.get("route") == "paper"},
    }
