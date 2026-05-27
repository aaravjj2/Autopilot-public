from __future__ import annotations

from datetime import date, datetime
from typing import Any, Protocol

from apex.domain.models import AccountSnapshot, OpportunityScore, Position, TradeProposal


class MarketDataClient(Protocol):
    def get_intraday_price(self, symbol: str) -> float: ...

    def get_daily_bars(self, symbol: str, lookback_days: int = 252) -> list[dict[str, Any]]: ...

    def get_fundamentals(self, symbol: str) -> dict[str, Any]: ...

    def get_sector(self, symbol: str) -> str: ...

    def get_earnings_date(self, symbol: str) -> date | None: ...


class OptionsDataClient(Protocol):
    def get_option_chain(self, symbol: str) -> dict[str, Any]: ...

    def get_iv_rank(self, symbol: str) -> float | None: ...


class PredictionMarketClient(Protocol):
    def get_macro_snapshot(self) -> list[dict[str, Any]]: ...

    def get_ticker_signal(self, symbol: str) -> dict[str, Any] | None: ...

    def get_intraday_macro_shift(self) -> list[dict[str, Any]]: ...


class BrokerClient(Protocol):
    def get_account_snapshot(self) -> AccountSnapshot: ...

    def preview_order(self, proposal: TradeProposal) -> tuple[bool, str]: ...

    def submit_order(self, proposal: TradeProposal) -> str: ...

    def monitor_fill(self, order_id: str, timeout_seconds: int = 300) -> tuple[bool, str]: ...

    def cancel_order(self, order_id: str) -> None: ...

    def get_positions(self) -> list[Position]: ...

    def get_order(self, order_id: str) -> dict[str, Any]: ...


class BrainClient(Protocol):
    def score_symbol(
        self,
        symbol: str,
        market_context: dict[str, Any],
        macro_context: list[dict[str, Any]],
        trade_memory: list[dict[str, Any]],
    ) -> OpportunityScore: ...


class AgentPanelClient(Protocol):
    def evaluate(
        self,
        opportunity: OpportunityScore,
        market_data: dict[str, Any],
        options_data: dict[str, Any] | None,
        pm_data: dict[str, Any] | None,
    ) -> TradeProposal | None: ...


class Clock(Protocol):
    def now(self) -> datetime: ...
