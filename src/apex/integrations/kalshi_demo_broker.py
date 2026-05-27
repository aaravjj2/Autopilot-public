"""Kalshi demo/production Trade API broker (real orders on Kalshi)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from apex.core.config import Settings
from apex.core.logging import get_logger
from apex.integrations.broker import Position
from apex.integrations.kalshi_trading import KalshiTradingClient

LOGGER = get_logger(__name__)


@dataclass
class KalshiDemoBroker:
    """Submit YES legs to Kalshi Trade API (demo or prod base URL)."""

    settings: Settings
    _client: KalshiTradingClient = field(init=False, repr=False)
    _orders: dict[str, dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._client = KalshiTradingClient(self.settings)

    def get_positions(self) -> list[Position]:
        return []

    def submit_yes_leg(self, ticker: str, stake_usd: float, price: float) -> str:
        result = self._client.create_yes_limit_buy(ticker, stake_usd, price)
        order_id = str(result["order_id"])
        self._orders[order_id] = result
        return order_id

    def monitor_fill(self, order_id: str, timeout_seconds: int = 300) -> tuple[bool, str]:
        if order_id.startswith("failed_"):
            return False, "simulated_submit_failure"
        return self._client.wait_for_fill(order_id, timeout_seconds=min(timeout_seconds, 120))

    def cancel_order(self, order_id: str) -> None:
        _ = order_id

    def get_order(self, order_id: str) -> dict[str, Any]:
        if order_id in self._orders:
            return {"id": order_id, "status": self._orders[order_id].get("status", "unknown")}
        try:
            return self._client.get_order(order_id)
        except Exception as exc:
            return {"id": order_id, "status": "failed", "error": str(exc)}

    def close_symbol_position(self, symbol: str) -> bool:
        _ = symbol
        return False
