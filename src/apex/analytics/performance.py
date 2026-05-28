"""APEX Performance Analytics - Sharpe, win rate, P&L attribution"""
from __future__ import annotations

import math
import logging
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Calculated performance metrics."""
    total_return_pct: float = 0.0
    annualized_return_pct: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown_pct: float = 0.0
    max_drawdown_duration_days: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    expectancy: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    avg_holding_period_hours: float = 0.0
    calmar_ratio: float = 0.0
    by_source: dict[str, dict] = None
    by_symbol: dict[str, dict] = None
    by_instrument: dict[str, dict] = None


class PerformanceAnalyzer:
    """Calculate comprehensive performance metrics."""
    
    def __init__(self):
        self._equity_curve: list[dict] = []
        self._trades: list[dict] = []
    
    def add_trade(self, trade: dict):
        """Add a completed trade."""
        self._trades.append(trade)
    
    def add_equity_point(self, timestamp: str, equity: float):
        """Add equity curve data point."""
        self._equity_curve.append({
            "timestamp": timestamp,
            "equity": equity,
        })
    
    def calculate_metrics(self, risk_free_rate: float = 0.05) -> PerformanceMetrics:
        """Calculate all performance metrics."""
        metrics = PerformanceMetrics()
        
        if not self._trades:
            return metrics
        
        # Trade-level metrics
        pnls = []
        wins = []
        losses = []
        by_source: dict[str, list] = {}
        by_symbol: dict[str, list] = {}
        by_instrument: dict[str, list] = {}
        holding_periods = []
        
        for trade in self._trades:
            pnl = trade.get("pnl", 0)
            pnls.append(pnl)
            
            if pnl > 0:
                wins.append(pnl)
            else:
                losses.append(pnl)
            
            # By source
            source = trade.get("source", "unknown")
            by_source.setdefault(source, []).append(pnl)
            
            # By symbol
            symbol = trade.get("symbol", "unknown")
            by_symbol.setdefault(symbol, []).append(pnl)
            
            # By instrument
            instrument = trade.get("instrument", "unknown")
            by_instrument.setdefault(instrument, []).append(pnl)
            
            # Holding period
            if trade.get("entry_time") and trade.get("exit_time"):
                try:
                    entry = datetime.fromisoformat(trade["entry_time"])
                    exit = datetime.fromisoformat(trade["exit_time"])
                    hours = (exit - entry).total_seconds() / 3600
                    holding_periods.append(hours)
                except (ValueError, TypeError, KeyError):
                    pass
        
        metrics.total_trades = len(pnls)
        metrics.winning_trades = len(wins)
        metrics.losing_trades = len(losses)
        metrics.win_rate = len(wins) / len(pnls) * 100 if pnls else 0
        
        metrics.avg_win = sum(wins) / len(wins) if wins else 0
        metrics.avg_loss = sum(losses) / len(losses) if losses else 0
        metrics.largest_win = max(wins) if wins else 0
        metrics.largest_loss = min(losses) if losses else 0
        
        total_return = sum(pnls)
        metrics.total_return_pct = total_return
        
        # Profit factor
        gross_profit = sum(w for w in wins if w > 0)
        gross_loss = abs(sum(loss for loss in losses if loss < 0))
        metrics.profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")
        
        # Expectancy
        metrics.expectancy = total_return / len(pnls) if pnls else 0
        
        # Average holding period
        metrics.avg_holding_period_hours = sum(holding_periods) / len(holding_periods) if holding_periods else 0
        
        # Equity curve metrics
        if self._equity_curve:
            equity_values = [p["equity"] for p in self._equity_curve]
            if len(equity_values) > 1:
                # Returns
                returns = []
                for i in range(1, len(equity_values)):
                    ret = (equity_values[i] - equity_values[i-1]) / equity_values[i-1]
                    returns.append(ret)
                
                if returns:
                    avg_return = sum(returns) / len(returns)
                    std_return = math.sqrt(sum((r - avg_return) ** 2 for r in returns) / len(returns)) if len(returns) > 1 else 1
                    
                    # Sharpe ratio (annualized)
                    if std_return > 0:
                        metrics.sharpe_ratio = (avg_return - risk_free_rate / 252) / std_return * math.sqrt(252)
                    
                    # Sortino ratio (downside deviation)
                    downside_returns = [r for r in returns if r < 0]
                    if downside_returns:
                        downside_std = math.sqrt(sum(r ** 2 for r in downside_returns) / len(downside_returns))
                        if downside_std > 0:
                            metrics.sortino_ratio = (avg_return - risk_free_rate / 252) / downside_std * math.sqrt(252)
                    
                    # Max drawdown
                    peak = equity_values[0]
                    max_dd = 0
                    max_dd_duration = 0
                    current_dd_start = None
                    
                    for i, eq in enumerate(equity_values):
                        if eq > peak:
                            peak = eq
                            current_dd_start = None
                        dd = (peak - eq) / peak * 100
                        if dd > max_dd:
                            max_dd = dd
                            if current_dd_start is None:
                                current_dd_start = i
                        if dd > 0 and current_dd_start is not None:
                            duration = i - current_dd_start
                            if duration > max_dd_duration:
                                max_dd_duration = duration
                    
                    metrics.max_drawdown_pct = max_dd
                    metrics.max_drawdown_duration_days = max_dd_duration
                    
                    # Calmar ratio
                    if metrics.max_drawdown_pct > 0:
                        metrics.calmar_ratio = metrics.total_return_pct / metrics.max_drawdown_pct
                    
                    # Annualized return
                    days = len(equity_values)
                    if days > 0:
                        start_equity = equity_values[0]
                        end_equity = equity_values[-1]
                        total_ret = (end_equity - start_equity) / start_equity
                        metrics.annualized_return_pct = total_ret * (365 / days) * 100
        
        # By source breakdown
        metrics.by_source = {}
        for source, source_pnls in by_source.items():
            source_wins = [p for p in source_pnls if p > 0]
            [p for p in source_pnls if p < 0]
            metrics.by_source[source] = {
                "trades": len(source_pnls),
                "win_rate": len(source_wins) / len(source_pnls) * 100 if source_pnls else 0,
                "total_pnl": sum(source_pnls),
                "avg_pnl": sum(source_pnls) / len(source_pnls) if source_pnls else 0,
            }
        
        # By symbol breakdown
        metrics.by_symbol = {}
        for symbol, symbol_pnls in by_symbol.items():
            metrics.by_symbol[symbol] = {
                "trades": len(symbol_pnls),
                "total_pnl": sum(symbol_pnls),
                "avg_pnl": sum(symbol_pnls) / len(symbol_pnls) if symbol_pnls else 0,
            }
        
        # By instrument breakdown
        metrics.by_instrument = {}
        for instrument, inst_pnls in by_instrument.items():
            metrics.by_instrument[instrument] = {
                "trades": len(inst_pnls),
                "total_pnl": sum(inst_pnls),
                "avg_pnl": sum(inst_pnls) / len(inst_pnls) if inst_pnls else 0,
            }
        
        return metrics


_singleton: PerformanceAnalyzer | None = None

def get_performance_analyzer() -> PerformanceAnalyzer:
    global _singleton
    if _singleton is None:
        _singleton = PerformanceAnalyzer()
    return _singleton
