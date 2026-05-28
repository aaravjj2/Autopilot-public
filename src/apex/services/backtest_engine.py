from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import statistics
from apex.core.config import Settings
from apex.core.logging import get_logger
from apex.domain.models import BacktestResult
from apex.repositories.sqlite_store import SQLiteStore

LOGGER = get_logger(__name__)

@dataclass
class BacktestEngine:
    settings: Settings
    store: SQLiteStore

    def run(self, lookback_days: int = 90) -> BacktestResult:
        """Replay resolved arb opportunities from the last N days."""
        (datetime.now(timezone.utc) - timedelta(days=lookback_days)).isoformat()
        resolved = self.store.get_resolved_arb_opportunities(limit=1000)

        if not resolved:
            LOGGER.warning("No resolved arb opportunities found for backtest")
            return BacktestResult(
                n_trades=0, n_wins=0, n_losses=0, n_pushes=0,
                win_rate=0.0, avg_net_edge=0.0, total_pnl=0.0,
                sharpe=0.0, edge_per_day=[], avg_hold_days=0.0,
                best_trade="", worst_trade="",
                annualized_roc=0.0, slippage_adjusted_sharpe=0.0,
                per_category_stats=[],
            )

        daily_pnl: dict[str, float] = {}
        pnls: list[float] = []
        pnls_slip: list[float] = []
        category_stats: dict[str, dict] = {}
        hold_days: list[float] = []
        wins = losses = pushes = 0
        best_pnl, worst_pnl = float("-inf"), float("inf")
        best_id = worst_id = ""

        for opp in resolved:
            pnl = opp.pnl or 0.0
            pnls.append(pnl)

            if opp.net_edge != 0:
                stake = abs(pnl / opp.net_edge) if pnl != 0 else 50.0
            else:
                stake = 50.0
            slip_pnl = pnl - (0.02 * stake)
            pnls_slip.append(slip_pnl)
            
            cat = opp.kalshi_ticker.split("-")[0] if "-" in opp.kalshi_ticker else "UNKNOWN"
            opp.category = cat
            
            if cat not in category_stats:
                category_stats[cat] = {"n_trades": 0, "n_wins": 0, "total_pnl": 0.0, "total_edge": 0.0}
            c_stat = category_stats[cat]
            c_stat["n_trades"] += 1
            if pnl > 0:
                c_stat["n_wins"] += 1
            c_stat["total_pnl"] += pnl
            c_stat["total_edge"] += opp.net_edge

            if pnl > 0:
                wins += 1
            elif pnl < 0:
                losses += 1
            else:
                pushes += 1

            if pnl > best_pnl:
                best_pnl = pnl
                best_id = opp.id
            if pnl < worst_pnl:
                worst_pnl = pnl
                worst_id = opp.id

            # Daily bucketing
            day_key = opp.detection_ts.date().isoformat() if opp.detection_ts else "unknown"
            daily_pnl[day_key] = daily_pnl.get(day_key, 0.0) + pnl

            # Hold time
            if opp.resolution_ts and opp.detection_ts:
                hold = (opp.resolution_ts - opp.detection_ts).total_seconds() / 86400
                hold_days.append(hold)

        # Cumulative edge per day
        sorted_days = sorted(daily_pnl.keys())
        cumulative = 0.0
        edge_per_day = []
        for day in sorted_days:
            cumulative += daily_pnl[day]
            edge_per_day.append((day, round(cumulative, 4)))

        # Sharpe (annualised, assume 252 trading days)
        sharpe = 0.0
        if len(pnls) >= 2:
            mu = statistics.mean(pnls)
            sigma = statistics.stdev(pnls)
            if sigma > 0:
                sharpe = round((mu / sigma) * (252 ** 0.5), 3)

        slip_sharpe = 0.0
        if len(pnls_slip) >= 2:
            mu_s = statistics.mean(pnls_slip)
            sigma_s = statistics.stdev(pnls_slip)
            if sigma_s > 0:
                slip_sharpe = round((mu_s / sigma_s) * (252 ** 0.5), 3)

        avg_hold_days = round(statistics.mean(hold_days), 1) if hold_days else 0.0
        avg_net_edge = round(statistics.mean([o.net_edge for o in resolved]), 4) if resolved else 0.0

        annualized_roc = 0.0
        if avg_hold_days > 0:
            annualized_roc = round((avg_net_edge / avg_hold_days) * 365, 4)

        # Calculate Max Drawdown
        max_drawdown = 0.0
        running_equity = 0.0
        peak_equity = 0.0
        for _, val in edge_per_day:
            running_equity = val
            if running_equity > peak_equity:
                peak_equity = running_equity
            
            dd = peak_equity - running_equity
            if dd > max_drawdown:
                max_drawdown = dd

        per_cat = []
        for c, s in category_stats.items():
            per_cat.append({
                "category": c,
                "n_trades": s["n_trades"],
                "win_rate": round(s["n_wins"] / s["n_trades"], 3) if s["n_trades"] else 0.0,
                "avg_edge": round(s["total_edge"] / s["n_trades"], 4) if s["n_trades"] else 0.0,
                "total_pnl": round(s["total_pnl"], 2),
            })

        n = len(resolved)
        return BacktestResult(
            n_trades=n,
            n_wins=wins,
            n_losses=losses,
            n_pushes=pushes,
            win_rate=round(wins / n, 3) if n else 0.0,
            avg_net_edge=avg_net_edge,
            total_pnl=round(sum(pnls), 4),
            sharpe=sharpe,
            edge_per_day=edge_per_day,
            avg_hold_days=avg_hold_days,
            best_trade=best_id,
            worst_trade=worst_id,
            annualized_roc=annualized_roc,
            slippage_adjusted_sharpe=slip_sharpe,
            max_drawdown=round(max_drawdown, 2),
            per_category_stats=per_cat,
        )
