"""APEX Discord Brain - Intelligent signal validation and execution"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from enum import Enum

logger = logging.getLogger(__name__)


class SignalVerdict(Enum):
    APPROVE = "approve"
    REJECT = "reject"
    MODIFY = "modify"
    DELAY = "delay"


class DiscordBrainConfig:
    """Configuration for the Discord brain."""
    # Trading hours (ET)
    market_open_hour = 9
    market_open_minute = 30
    market_close_hour = 16
    
    # Risk limits for Discord signals
    max_position_size_pct = 5.0  # Max 5% of portfolio per Discord trade
    max_daily_discord_trades = 10  # Max Discord trades per day
    min_days_to_expiration = 3  # Don't trade options expiring in < 3 days
    max_days_to_expiration = 60  # Don't trade options > 60 days out
    min_liquidity_volume = 100  # Min daily volume for the option
    
    # Signal quality thresholds
    min_conviction_score = 7.0  # Bullseye signals start at 8.0
    max_correlation_risk = 0.7  # Don't add if highly correlated with existing positions
    
    # Position sizing
    base_position_size = 1  # Default contracts
    max_contracts_per_trade = 5
    
    # Stop loss / take profit
    default_stop_loss_pct = 0.30  # 30% loss from entry
    default_take_profit_pct = 0.50  # 50% gain from entry
    
    # Cooldown
    signal_cooldown_minutes = 30  # Don't trade same symbol within 30 min


class DiscordBrain:
    """
    Intelligent brain for Discord Bullseye signals.
    
    Validates signals against market conditions, risk limits, and historical
    performance before deciding whether to execute a trade.
    """
    
    def __init__(self, config: DiscordBrainConfig | None = None):
        self.config = config or DiscordBrainConfig()
        self._recent_trades: dict[str, datetime] = {}  # symbol -> last trade time
        self._signal_history: list[dict] = []
        self._source_performance: dict[str, dict] = {}
    
    def _make_verdict(
        self,
        verdict: SignalVerdict,
        reason: str,
        signal: dict,
        **kwargs,
    ) -> dict[str, Any]:
        """Create a standardized verdict response."""
        result = {
            "verdict": verdict.value,
            "reason": reason,
            "signal": signal,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        }
        result.update(kwargs)
        return result
    
    async def evaluate_signal(self, signal: dict[str, Any], portfolio_state: dict) -> dict[str, Any]:
        """
        Full evaluation pipeline for a Discord signal.
        
        Returns evaluation result with verdict and reasoning.
        """
        ticker = signal.get("ticker", "")
        strike = signal.get("strike", 0)
        expiration = signal.get("expiration", "")
        option_type = signal.get("type", "")
        
        logger.info(f"🧠 Evaluating Discord signal: {ticker} ${strike} {option_type} exp {expiration}")
        
        # Step 1: Market conditions check
        market_check = self._check_market_conditions()
        if not market_check["approved"]:
            return self._make_verdict(
                SignalVerdict.REJECT,
                f"Market conditions: {market_check['reason']}",
                signal,
            )
        
        # Step 2: Signal validation
        validation = self._validate_signal(signal)
        if not validation["approved"]:
            return self._make_verdict(
                SignalVerdict.REJECT,
                f"Signal validation: {validation['reason']}",
                signal,
            )
        
        # Step 3: Risk assessment
        risk_check = self._assess_risk(signal, portfolio_state)
        if not risk_check["approved"]:
            return self._make_verdict(
                SignalVerdict.REJECT,
                f"Risk assessment: {risk_check['reason']}",
                signal,
            )
        
        # Step 4: Source quality check
        source_quality = self._check_source_quality(signal.get("source", "discord_bullseye"))
        
        # Step 5: Calculate position size
        position_size = self._calculate_position_size(
            signal=signal,
            portfolio_state=portfolio_state,
            source_quality=source_quality,
        )
        
        # Step 6: Set stop loss and take profit
        sl_tp = self._calculate_exit_levels(signal, position_size)
        
        # Step 7: Final conviction adjustment
        final_conviction = self._adjust_conviction(
            base_conviction=8.0,
            source_quality=source_quality,
            risk_score=risk_check.get("risk_score", 50),
            market_conditions=market_check,
        )
        
        # Decision
        if final_conviction >= self.config.min_conviction_score:
            return self._make_verdict(
                SignalVerdict.APPROVE,
                "Signal approved for execution",
                signal,
                position_size=position_size,
                stop_loss=sl_tp["stop_loss"],
                take_profit=sl_tp["take_profit"],
                estimated_entry=sl_tp["estimated_entry"],
                conviction=final_conviction,
                risk_score=risk_check.get("risk_score", 50),
            )
        else:
            return self._make_verdict(
                SignalVerdict.REJECT,
                f"Adjusted conviction {final_conviction:.1f} below minimum {self.config.min_conviction_score}",
                signal,
            )
    
    def _check_market_conditions(self) -> dict:
        """Check if market conditions are suitable for trading."""
        from zoneinfo import ZoneInfo
        
        et = ZoneInfo("America/New_York")
        now = datetime.now(et)
        
        # Check if it's a weekday
        if now.weekday() >= 5:
            return {"approved": False, "reason": "Weekend - markets closed"}
        
        # Check market hours
        current_hour = now.hour
        current_minute = now.minute
        current_time = current_hour * 60 + current_minute
        
        market_open_minutes = self.config.market_open_hour * 60 + self.config.market_open_minute
        market_close_minutes = self.config.market_close_hour * 60
        
        if current_time < market_open_minutes:
            return {"approved": False, "reason": f"Market not open yet (opens {self.config.market_open_hour}:{self.config.market_open_minute:02d} ET)"}
        
        if current_time > market_close_minutes:
            return {"approved": False, "reason": "Market closed for the day"}
        
        return {"approved": True, "reason": "Market open"}
    
    def _validate_signal(self, signal: dict) -> dict:
        """Validate signal parameters."""
        ticker = signal.get("ticker", "")
        strike = signal.get("strike", 0)
        expiration = signal.get("expiration", "")
        option_type = signal.get("type", "")
        
        if not ticker:
            return {"approved": False, "reason": "No ticker provided"}
        
        if strike <= 0:
            return {"approved": False, "reason": "Invalid strike price"}
        
        if option_type not in ("CALL", "PUT"):
            return {"approved": False, "reason": f"Invalid option type: {option_type}"}
        
        # Check expiration
        try:
            exp_date = datetime.strptime(expiration, "%m/%d/%Y")
            days_to_exp = (exp_date - datetime.now()).days
            
            if days_to_exp < self.config.min_days_to_expiration:
                return {
                    "approved": False,
                    "reason": f"Expiration too close ({days_to_exp} days, min {self.config.min_days_to_expiration})",
                }
            
            if days_to_exp > self.config.max_days_to_expiration:
                return {
                    "approved": False,
                    "reason": f"Expiration too far ({days_to_exp} days, max {self.config.max_days_to_expiration})",
                }
        except ValueError:
            return {"approved": False, "reason": f"Invalid expiration format: {expiration}"}
        
        # Check cooldown
        last_trade = self._recent_trades.get(ticker)
        if last_trade:
            minutes_since = (datetime.now(tz=timezone.utc) - last_trade).total_seconds() / 60
            if minutes_since < self.config.signal_cooldown_minutes:
                return {
                    "approved": False,
                    "reason": f"Cooldown active for {ticker} ({minutes_since:.0f}m < {self.config.signal_cooldown_minutes}m)",
                }
        
        return {"approved": True, "reason": "Signal valid"}
    
    def _assess_risk(self, signal: dict, portfolio_state: dict) -> dict:
        """Assess risk of the proposed trade."""
        equity = float(portfolio_state.get("equity", 100000))
        positions = portfolio_state.get("positions", [])
        daily_trades = portfolio_state.get("trades_today", 0)
        
        # Check daily trade limit
        if daily_trades >= self.config.max_daily_discord_trades:
            return {
                "approved": False,
                "reason": f"Daily Discord trade limit reached ({daily_trades}/{self.config.max_daily_discord_trades})",
                "risk_score": 100,
            }
        
        # Check position concentration
        ticker = signal.get("ticker", "")
        existing_positions = [p for p in positions if p.get("ticker") == ticker]
        if existing_positions:
            return {
                "approved": False,
                "reason": f"Already have position in {ticker}",
                "risk_score": 80,
            }
        
        # Check sector concentration (simplified)
        sector = portfolio_state.get("sectors", {}).get(ticker, "Unknown")
        sector_exposure = portfolio_state.get("sectors", {}).get(sector, 0)
        sector_pct = sector_exposure / equity * 100 if equity > 0 else 0
        
        if sector_pct > 25:  # 25% sector limit for Discord trades
            return {
                "approved": False,
                "reason": f"Sector {sector} concentration too high ({sector_pct:.1f}%)",
                "risk_score": 70,
            }
        
        # Calculate risk score
        risk_score = 0
        
        # Higher risk for short-dated options
        try:
            exp_date = datetime.strptime(signal.get("expiration", ""), "%m/%d/%Y")
            days_to_exp = (exp_date - datetime.now()).days
            if days_to_exp < 7:
                risk_score += 30
            elif days_to_exp < 14:
                risk_score += 15
        except (ValueError, TypeError, KeyError):
            risk_score += 20
        
        # Higher risk for deep OTM options
        # (Would need current stock price to calculate - simplified here)
        
        return {
            "approved": True,
            "reason": "Risk acceptable",
            "risk_score": risk_score,
        }
    
    def _check_source_quality(self, source: str) -> dict:
        """Check historical performance of the signal source."""
        if source in self._source_performance:
            perf = self._source_performance[source]
            return {
                "quality_score": perf.get("win_rate", 50),
                "total_signals": perf.get("total", 0),
                "win_rate": perf.get("win_rate", 50),
                "avg_pnl": perf.get("avg_pnl", 0),
            }
        
        # Default for new sources
        return {
            "quality_score": 50,
            "total_signals": 0,
            "win_rate": 50,
            "avg_pnl": 0,
        }
    
    def _calculate_position_size(
        self,
        signal: dict,
        portfolio_state: dict,
        source_quality: dict,
    ) -> int:
        """Calculate optimal number of contracts."""
        equity = float(portfolio_state.get("equity", 100000))
        
        # Max notional based on portfolio
        max_notional = equity * (self.config.max_position_size_pct / 100)
        
        # Estimate option premium (rough estimate - would use real pricing in production)
        strike = signal.get("strike", 0)
        estimated_premium = strike * 0.05  # Rough 5% of strike as premium estimate
        estimated_cost = estimated_premium * 100  # Per contract
        
        if estimated_cost <= 0:
            return self.config.base_position_size
        
        # Calculate contracts
        contracts = int(max_notional / estimated_cost)
        contracts = max(1, min(contracts, self.config.max_contracts_per_trade))
        
        # Adjust based on source quality
        quality_factor = source_quality.get("quality_score", 50) / 100
        contracts = max(1, int(contracts * quality_factor))
        
        return contracts
    
    def _calculate_exit_levels(self, signal: dict, contracts: int) -> dict:
        """Calculate stop-loss and take-profit levels."""
        strike = signal.get("strike", 0)
        estimated_premium = strike * 0.05
        
        stop_loss = estimated_premium * (1 - self.config.default_stop_loss_pct)
        take_profit = estimated_premium * (1 + self.config.default_take_profit_pct)
        
        return {
            "stop_loss": round(stop_loss, 2),
            "take_profit": round(take_profit, 2),
            "estimated_entry": round(estimated_premium, 2),
        }
    
    def _adjust_conviction(
        self,
        base_conviction: float,
        source_quality: dict,
        risk_score: int,
        market_conditions: dict,
    ) -> float:
        """Adjust conviction based on multiple factors."""
        conviction = base_conviction
        
        # Source quality adjustment
        quality_score = source_quality.get("quality_score", 50)
        if quality_score > 60:
            conviction += (quality_score - 50) / 20  # +0 to +0.5
        elif quality_score < 40:
            conviction -= (50 - quality_score) / 20  # -0 to -0.5
        
        # Risk adjustment
        if risk_score > 50:
            conviction -= (risk_score - 50) / 25  # -0 to -2.0
        
        # Market conditions adjustment
        if not market_conditions.get("approved", False):
            conviction -= 3.0
        
        return max(0, min(10, conviction))
    
    def record_trade_outcome(self, signal_id: str, pnl: float, pnl_pct: float):
        """Record the outcome of a trade for learning."""
        self._signal_history.append({
            "signal_id": signal_id,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        })
        
        # Update source performance
        # (Would be linked to source in production)
    
    def get_brain_stats(self) -> dict:
        """Get brain statistics."""
        return {
            "total_signals_evaluated": len(self._signal_history),
            "recent_trades": len(self._recent_trades),
            "source_performance": self._source_performance,
            "config": {
                "max_position_size_pct": self.config.max_position_size_pct,
                "max_daily_discord_trades": self.config.max_daily_discord_trades,
                "min_conviction_score": self.config.min_conviction_score,
                "signal_cooldown_minutes": self.config.signal_cooldown_minutes,
            },
        }


_singleton: DiscordBrain | None = None

def get_discord_brain(config: DiscordBrainConfig | None = None) -> DiscordBrain:
    global _singleton
    if _singleton is None:
        _singleton = DiscordBrain(config)
    return _singleton
