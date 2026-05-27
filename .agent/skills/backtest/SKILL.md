---
name: backtest
description: >
  Use this skill to build or run the MarketMind backtest engine — replaying resolved
  arb_opportunities rows through the arb logic to compute win rate, Sharpe ratio, and
  edge-per-day. Also covers the /api/arb/backtest FastAPI endpoint and the analytics
  tab in the Next.js dashboard.
compatibility: Antigravity CLI (agy), Claude Code, Gemini CLI
---

# Backtest Engine Skill

## BacktestResult Dataclass

```python
@dataclass
class BacktestResult:
    n_trades: int
    n_wins: int
    n_losses: int
    n_pushes: int
    win_rate: float                     # n_wins / n_trades
    avg_net_edge: float
    total_pnl: float
    sharpe: float                       # annualised
    edge_per_day: list[tuple[str, float]]  # [(date_str, cumulative_pnl), ...]
    avg_hold_days: float                # average calendar days until resolution
    best_trade: str                     # arb_id of highest pnl
    worst_trade: str                    # arb_id of lowest pnl
```

---

## BacktestEngine Implementation

```python
# src/apex/services/backtest_engine.py
from __future__ import annotations
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
import statistics
from apex.core.config import Settings
from apex.core.logging import get_logger
from apex.domain.models import ArbOpportunity, BacktestResult
from apex.repositories.sqlite_store import SQLiteStore

LOGGER = get_logger(__name__)

@dataclass
class BacktestEngine:
    settings: Settings
    store: SQLiteStore

    def run(self, lookback_days: int = 90) -> BacktestResult:
        """Replay resolved arb opportunities from the last N days."""
        cutoff = (datetime.utcnow() - timedelta(days=lookback_days)).isoformat()
        resolved = self.store.get_resolved_arb_opportunities(since=cutoff)

        if not resolved:
            LOGGER.warning("No resolved arb opportunities found for backtest")
            return BacktestResult(
                n_trades=0, n_wins=0, n_losses=0, n_pushes=0,
                win_rate=0.0, avg_net_edge=0.0, total_pnl=0.0,
                sharpe=0.0, edge_per_day=[], avg_hold_days=0.0,
                best_trade="", worst_trade="",
            )

        daily_pnl: dict[str, float] = {}
        pnls: list[float] = []
        hold_days: list[float] = []
        wins = losses = pushes = 0
        best_pnl, worst_pnl = float("-inf"), float("inf")
        best_id = worst_id = ""

        for opp in resolved:
            pnl = opp.pnl or 0.0
            pnls.append(pnl)

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
        if len(pnls) >= 5:
            mu     = statistics.mean(pnls)
            sigma  = statistics.stdev(pnls) or 1e-9
            sharpe = round((mu / sigma) * (252 ** 0.5), 3)

        n = len(resolved)
        return BacktestResult(
            n_trades=n,
            n_wins=wins,
            n_losses=losses,
            n_pushes=pushes,
            win_rate=round(wins / n, 3) if n else 0.0,
            avg_net_edge=round(statistics.mean([o.net_edge for o in resolved]), 4),
            total_pnl=round(sum(pnls), 4),
            sharpe=sharpe,
            edge_per_day=edge_per_day,
            avg_hold_days=round(statistics.mean(hold_days), 1) if hold_days else 0.0,
            best_trade=best_id,
            worst_trade=worst_id,
        )
```

---

## SQLiteStore Methods Needed

```python
# Add to src/apex/repositories/sqlite_store.py

def get_resolved_arb_opportunities(self, since: str) -> list[ArbOpportunity]:
    rows = self._conn.execute(
        """SELECT * FROM arb_opportunities
           WHERE outcome IS NOT NULL
           AND detection_ts >= ?
           ORDER BY detection_ts ASC""",
        (since,)
    ).fetchall()
    result = []
    for row in rows:
        opp = ArbOpportunity(
            id=row[0],
            kalshi_ticker=row[1],
            poly_market_id=row[2],
            question=row[3],
            kalshi_yes_ask=row[4],
            poly_no_ask=row[5],
            gross_spread=row[6],
            net_edge=row[7],
            settlement_match_score=row[8],
            settlement_flags=json.loads(row[9] or "[]"),
            detection_ts=datetime.fromisoformat(row[10]) if row[10] else datetime.utcnow(),
            resolution_ts=datetime.fromisoformat(row[11]) if row[11] else None,
            outcome=row[12],
            pnl=row[13],
            volume_kalshi=row[15] or 0.0,
            volume_poly=row[16] or 0.0,
        )
        result.append(opp)
    return result
```

---

## FastAPI Endpoint

```python
# Add to autopilot-local/backend/main.py

from apex.services.backtest_engine import BacktestEngine
from apex.core.config import get_settings
from apex.repositories.sqlite_store import SQLiteStore

@app.get("/api/arb/backtest")
async def get_backtest(lookback_days: int = 90):
    settings = get_settings()
    store    = SQLiteStore(settings.sqlite_path)
    engine   = BacktestEngine(settings=settings, store=store)
    result   = engine.run(lookback_days=lookback_days)
    return {
        "n_trades":      result.n_trades,
        "win_rate":      result.win_rate,
        "sharpe":        result.sharpe,
        "total_pnl":     result.total_pnl,
        "avg_net_edge":  result.avg_net_edge,
        "avg_hold_days": result.avg_hold_days,
        "edge_per_day":  result.edge_per_day,
    }
```

---

## Analytics Tab (Next.js, Recharts)

```tsx
// autopilot-local/frontend/app/dashboard/analytics/BacktestTab.tsx
"use client";
import { useEffect, useState } from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

export function BacktestTab() {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    fetch("/api/arb/backtest?lookback_days=90")
      .then(r => r.json())
      .then(setData);
  }, []);

  if (!data) return <p className="text-sm text-gray-500">Loading backtest…</p>;

  const chartData = data.edge_per_day.map(([date, pnl]: [string, number]) => ({
    date, pnl: Number(pnl.toFixed(4))
  }));

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-4 gap-3">
        {[
          { label: "Trades", value: data.n_trades },
          { label: "Win Rate", value: `${(data.win_rate * 100).toFixed(1)}%` },
          { label: "Sharpe", value: data.sharpe.toFixed(2) },
          { label: "Avg Edge", value: `$${data.avg_net_edge.toFixed(3)}` },
        ].map(stat => (
          <div key={stat.label} className="bg-white rounded-lg border p-3">
            <p className="text-xs text-gray-500">{stat.label}</p>
            <p className="text-xl font-bold text-gray-900">{stat.value}</p>
          </div>
        ))}
      </div>
      <div className="bg-white rounded-lg border p-4">
        <p className="text-sm font-medium text-gray-700 mb-3">Cumulative P&amp;L (90d)</p>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" tick={{ fontSize: 10 }} />
            <YAxis tick={{ fontSize: 10 }} />
            <Tooltip />
            <Line type="monotone" dataKey="pnl" stroke="#0f6e56" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
```
