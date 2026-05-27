"""APEX Risk Management Engine - Portfolio-level risk controls"""
from __future__ import annotations

import math
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timezone, timedelta
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class RiskLimits:
    """Portfolio-level risk limits."""
    max_drawdown_pct: float = 15.0  # Max portfolio drawdown %
    max_daily_loss_pct: float = 3.0  # Max daily loss %
    max_position_size_pct: float = 10.0  # Max single position % of portfolio
    max_sector_concentration_pct: float = 30.0  # Max sector exposure %
    max_correlated_exposure_pct: float = 40.0  # Max correlated positions %
    max_options_premium_pct: float = 5.0  # Max options premium as % of portfolio
    max_open_positions: int = 20  # Max simultaneous open positions
    max_daily_trades: int = 50  # Max trades per day
    min_conviction_score: float = 6.0  # Minimum conviction to trade


@dataclass
class PortfolioState:
    """Current portfolio state for risk checks."""
    equity: float = 100000.0
    peak_equity: float = 100000.0
    daily_pl: float = 0.0
    daily_pl_pct: float = 0.0
    positions: list[dict] = field(default_factory=list)
    sectors: dict[str, float] = field(default_factory=dict)
    open_orders: int = 0
    trades_today: int = 0
    options_exposure: float = 0.0


@dataclass
class RiskCheckResult:
    """Result of a risk check."""
    approved: bool
    reason: str = ""
    suggested_size: float = 0.0
    risk_score: float = 0.0  # 0-100, higher = riskier


class RiskEngine:
    """Portfolio-level risk management engine."""
    
    def __init__(self, limits: RiskLimits | None = None):
        self.limits = limits or RiskLimits()
        self._circuit_breaker_active = False
        self._last_reset = datetime.now(tz=timezone.utc)
    
    def check_portfolio_risk(self, state: PortfolioState) -> RiskCheckResult:
        """Check overall portfolio risk level."""
        reasons = []
        risk_score = 0.0
        
        # Drawdown check
        drawdown = (state.peak_equity - state.equity) / state.peak_equity * 100 if state.peak_equity > 0 else 0
        if drawdown > self.limits.max_drawdown_pct:
            self._circuit_breaker_active = True
            reasons.append(f"Drawdown {drawdown:.1f}% exceeds limit {self.limits.max_drawdown_pct}%")
            risk_score += 40
        
        # Daily loss check
        if abs(state.daily_pl_pct) > self.limits.max_daily_loss_pct:
            self._circuit_breaker_active = True
            reasons.append(f"Daily loss {state.daily_pl_pct:.1f}% exceeds limit {self.limits.max_daily_loss_pct}%")
            risk_score += 30
        
        # Position count check
        if len(state.positions) >= self.limits.max_open_positions:
            reasons.append(f"Max positions ({self.limits.max_open_positions}) reached")
            risk_score += 10
        
        # Trade frequency check
        if state.trades_today >= self.limits.max_daily_trades:
            reasons.append(f"Max daily trades ({self.limits.max_daily_trades}) reached")
            risk_score += 10
        
        # Sector concentration check
        for sector, exposure in state.sectors.items():
            sector_pct = exposure / state.equity * 100 if state.equity > 0 else 0
            if sector_pct > self.limits.max_sector_concentration_pct:
                reasons.append(f"Sector {sector} concentration {sector_pct:.1f}% exceeds limit")
                risk_score += 15
        
        return RiskCheckResult(
            approved=len(reasons) == 0 and not self._circuit_breaker_active,
            reason="; ".join(reasons) if reasons else "OK",
            risk_score=min(risk_score, 100),
        )
    
    def check_trade_risk(
        self,
        state: PortfolioState,
        symbol: str,
        side: str,
        instrument: str,
        notional: float,
        conviction: float = 5.0,
        sector: str = "",
    ) -> RiskCheckResult:
        """Check if a specific trade passes risk limits."""
        # First check portfolio-level risk
        portfolio_check = self.check_portfolio_risk(state)
        if not portfolio_check.approved:
            return RiskCheckResult(
                approved=False,
                reason=f"Portfolio risk: {portfolio_check.reason}",
                risk_score=portfolio_check.risk_score,
            )
        
        reasons = []
        risk_score = 0.0
        
        # Conviction check
        if conviction < self.limits.min_conviction_score:
            reasons.append(f"Conviction {conviction:.1f} below minimum {self.limits.min_conviction_score}")
            risk_score += 20
        
        # Position size check
        position_pct = notional / state.equity * 100 if state.equity > 0 else 100
        if position_pct > self.limits.max_position_size_pct:
            reasons.append(f"Position size {position_pct:.1f}% exceeds limit {self.limits.max_position_size_pct}%")
            risk_score += 25
        
        # Options premium check
        if instrument.upper() in ("OPTION", "OPTIONS"):
            options_pct = (state.options_exposure + notional) / state.equity * 100 if state.equity > 0 else 100
            if options_pct > self.limits.max_options_premium_pct:
                reasons.append(f"Options exposure {options_pct:.1f}% exceeds limit")
                risk_score += 20
        
        # Calculate suggested position size using Kelly criterion approximation
        suggested_size = self._calculate_position_size(
            state=state,
            conviction=conviction,
            instrument=instrument,
        )
        
        return RiskCheckResult(
            approved=len(reasons) == 0,
            reason="; ".join(reasons) if reasons else "OK",
            suggested_size=suggested_size,
            risk_score=min(risk_score, 100),
        )
    
    def _calculate_position_size(
        self,
        state: PortfolioState,
        conviction: float,
        instrument: str,
    ) -> float:
        """Calculate optimal position size using volatility-adjusted Kelly."""
        # Base size as % of portfolio
        base_pct = self.limits.max_position_size_pct / 100
        
        # Conviction adjustment (0.5x to 1.5x)
        conviction_factor = 0.5 + (conviction / 10.0)
        
        # Instrument risk adjustment
        instrument_factor = 0.5 if instrument.upper() in ("OPTION", "OPTIONS") else 1.0
        
        # Portfolio utilization adjustment
        utilization = len(state.positions) / self.limits.max_open_positions if self.limits.max_open_positions > 0 else 0
        utilization_factor = 1.0 - (utilization * 0.5)  # Reduce size as portfolio fills
        
        suggested_pct = base_pct * conviction_factor * instrument_factor * utilization_factor
        suggested_notional = state.equity * min(suggested_pct, self.limits.max_position_size_pct / 100)
        
        return max(suggested_notional, 0)
    
    def reset_circuit_breaker(self):
        """Reset circuit breaker (should only be called manually or after cooldown)."""
        self._circuit_breaker_active = False
        self._last_reset = datetime.now(tz=timezone.utc)
        logger.info("Circuit breaker reset")
    
    def get_risk_summary(self, state: PortfolioState) -> dict:
        """Get comprehensive risk summary."""
        portfolio_check = self.check_portfolio_risk(state)
        
        drawdown = (state.peak_equity - state.equity) / state.peak_equity * 100 if state.peak_equity > 0 else 0
        
        sector_exposure = {}
        for sector, value in state.sectors.items():
            sector_exposure[sector] = {
                "value": value,
                "pct": value / state.equity * 100 if state.equity > 0 else 0,
            }
        
        return {
            "circuit_breaker_active": self._circuit_breaker_active,
            "drawdown_pct": round(drawdown, 2),
            "daily_pl_pct": round(state.daily_pl_pct, 2),
            "position_count": len(state.positions),
            "trades_today": state.trades_today,
            "risk_score": portfolio_check.risk_score,
            "approved": portfolio_check.approved,
            "reason": portfolio_check.reason,
            "sector_exposure": sector_exposure,
            "limits": {
                "max_drawdown_pct": self.limits.max_drawdown_pct,
                "max_daily_loss_pct": self.limits.max_daily_loss_pct,
                "max_position_size_pct": self.limits.max_position_size_pct,
                "max_open_positions": self.limits.max_open_positions,
            },
        }


# Singleton
_risk_engine: RiskEngine | None = None

def get_risk_engine(limits: RiskLimits | None = None) -> RiskEngine:
    global _risk_engine
    if _risk_engine is None:
        _risk_engine = RiskEngine(limits)
    return _risk_engine
