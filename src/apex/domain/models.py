from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from apex.domain.enums import Direction, EventType, Instrument, PMSignal, RiskAction

_PM_OUTCOMES = frozenset({"YES", "NO"})


class OpportunityScore(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    direction: Direction
    instrument: Instrument
    conviction: float = Field(ge=0, le=10)
    technical_score: float = Field(ge=0, le=10)
    fundamental_score: float = Field(ge=0, le=10)
    pm_signal: PMSignal
    pm_divergence: float = Field(ge=-1, le=1)
    catalyst: str
    risk_reward: float = Field(gt=0)
    options_structure: dict[str, Any] | None = None
    max_position_pct: float = Field(gt=0)
    invalidation: str


class SpreadLeg(BaseModel):
    side: str
    option_type: str
    strike: float
    expiry_date: date
    quantity: int = Field(gt=0)


class TradeProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    direction: Direction
    instrument: Instrument
    entry_price: float = Field(gt=0)
    position_size_pct: float = Field(gt=0)
    stop_loss: float = Field(gt=0)
    take_profit: float = Field(gt=0)
    max_loss_dollars: float = Field(gt=0)
    expiry_date: date | None = None
    strike: float | None = None
    spread_legs: list[SpreadLeg] | None = None
    conviction_final: float = Field(ge=0, le=10)
    judge_rationale: str
    dissenting_view: str
    sector: str = "UNKNOWN"
    iv_rank: float | None = None
    earnings_date: date | None = None
    dexter_severity: float | None = None
    dexter_reduction_applied: bool = False
    polymarket_market_id: str = ""
    polymarket_outcome_side: str = ""
    polymarket_stake_usd: float = Field(default=0.0, ge=0.0)
    polymarket_question: str = ""

    @model_validator(mode="after")
    def validate_instrument_fields(self) -> "TradeProposal":
        if self.instrument == Instrument.POLYMARKET_EVENT:
            if not (self.polymarket_market_id and str(self.polymarket_market_id).strip()):
                raise ValueError("polymarket_market_id required for POLYMARKET_EVENT")
            side = str(self.polymarket_outcome_side).upper().strip()
            if side not in _PM_OUTCOMES:
                raise ValueError("polymarket_outcome_side must be YES or NO")
            if float(self.polymarket_stake_usd) <= 0:
                raise ValueError("polymarket_stake_usd must be positive for POLYMARKET_EVENT")
            self.polymarket_outcome_side = side
            return self
        if self.instrument in {
            Instrument.CALL,
            Instrument.PUT,
            Instrument.VERTICAL,
            Instrument.STRADDLE,
            Instrument.IRON_CONDOR,
        }:
            if self.expiry_date is None:
                raise ValueError("expiry_date required for options instruments")
            if self.instrument in {Instrument.CALL, Instrument.PUT} and self.strike is None:
                raise ValueError("strike required for CALL/PUT")
            if self.instrument in {Instrument.VERTICAL, Instrument.STRADDLE, Instrument.IRON_CONDOR}:
                if not self.spread_legs:
                    raise ValueError("spread_legs required for spread instruments")
        return self


@dataclass(slots=True)
class Position:
    symbol: str
    qty: float
    market_value: float
    sector: str
    avg_entry_price: float
    side: str
    correlation_to_book: float = 0.0
    entry_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class AccountSnapshot:
    equity: float
    buying_power: float
    daily_pl_pct: float
    open_positions: list[Position]


@dataclass(slots=True)
class RiskResult:
    risk_id: str
    passed: bool
    reason: str
    action: RiskAction


class AuditEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    event_type: EventType
    symbol: str | None = None
    agent: str | None = None
    conviction: float | None = None
    risk_check: str | None = None
    rejection_reason: str | None = None
    order_id: str | None = None
    pl_realized: float | None = None
    pm_signal: str | None = None
    raw_payload: dict[str, Any] = Field(default_factory=dict)


class AgentSignalAttribution(BaseModel):
    symbol: str
    closed_at: datetime
    technical_correct: bool
    fundamental_correct: bool
    pm_correct: bool
    dexter_helpful: bool
    pl_realized: float


@dataclass
class ArbOpportunity:
    kalshi_ticker: str
    poly_market_id: str
    question: str
    kalshi_title: str
    poly_title: str
    kalshi_yes_ask: float
    poly_no_ask: float
    gross_spread: float
    net_edge: float
    settlement_match_score: float
    settlement_flags: list[str]
    detection_ts: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    id: str = field(default_factory=lambda: uuid4().hex[:12])
    resolution_ts: datetime | None = None
    outcome: str | None = None
    pnl: float | None = None
    volume_kalshi: float = 0.0
    volume_poly: float = 0.0
    category: str = "UNKNOWN"
    kelly_fraction: float = 0.0
    vwap_edge: float = 0.0
    thesis_settlement_verdict: str | None = None
    web_context: dict[str, object] | None = None


@dataclass
class ArbThesis:
    arb_id: str = ""
    settlement_verdict: str = "CAUTION"
    settlement_explanation: str = ""
    divergence_reason: str = ""
    bull_case: str = ""
    bear_case: str = ""
    recommended_leg: str = "SKIP"
    net_edge_estimate: float = 0.0
    annualised_sharpe: float | None = None
    confidence: str = "LOW"
    risk_flags: list[str] = field(default_factory=list)
    one_liner: str = ""
    llm_provider: str = "none"
    generated_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))


@dataclass
class BacktestResult:
    n_trades: int
    n_wins: int
    n_losses: int
    n_pushes: int
    win_rate: float
    avg_net_edge: float
    total_pnl: float
    sharpe: float
    edge_per_day: list[tuple[str, float]]
    avg_hold_days: float
    best_trade: str
    worst_trade: str
    annualized_roc: float = 0.0
    slippage_adjusted_sharpe: float = 0.0
    max_drawdown: float = 0.0
    per_category_stats: list[dict] = field(default_factory=list)


@dataclass
class SettlementVerdict:
    match_score: float
    flags: list[str]
    recommendation: str

    @property
    def is_safe(self) -> bool:
        return self.recommendation == "SAFE"
