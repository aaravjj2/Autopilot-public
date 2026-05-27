"""CFTC positional limit tracking (Week 6 Day 4)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


DEFAULT_CONTRACT_LIMIT_USD = 250_000.0


@dataclass
class PositionExposure:
    contract_key: str
    notional_usd: float
    limit_usd: float = DEFAULT_CONTRACT_LIMIT_USD

    @property
    def utilization_pct(self) -> float:
        if self.limit_usd <= 0:
            return 100.0
        return min(100.0, (self.notional_usd / self.limit_usd) * 100.0)

    @property
    def headroom_usd(self) -> float:
        return max(0.0, self.limit_usd - self.notional_usd)

    @property
    def breached(self) -> bool:
        return self.notional_usd > self.limit_usd


@dataclass
class CftcLimitTracker:
    """Track per-contract notional vs $250k CFTC-style cap."""

    limit_usd: float = DEFAULT_CONTRACT_LIMIT_USD
    exposures: Dict[str, float] = field(default_factory=dict)

    def add_exposure(self, contract_key: str, notional_usd: float) -> None:
        self.exposures[contract_key] = self.exposures.get(contract_key, 0.0) + notional_usd

    def set_exposure(self, contract_key: str, notional_usd: float) -> None:
        self.exposures[contract_key] = notional_usd

    def check(self, contract_key: str, additional_usd: float = 0.0) -> PositionExposure:
        current = self.exposures.get(contract_key, 0.0) + additional_usd
        return PositionExposure(
            contract_key=contract_key,
            notional_usd=current,
            limit_usd=self.limit_usd,
        )

    def all_positions(self) -> list[PositionExposure]:
        return [
            PositionExposure(k, v, self.limit_usd)
            for k, v in sorted(self.exposures.items(), key=lambda x: -x[1])
        ]

    def breaches(self) -> list[PositionExposure]:
        return [p for p in self.all_positions() if p.breached]
