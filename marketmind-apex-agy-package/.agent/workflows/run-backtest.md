---
name: run-backtest
description: >
  Build the BacktestEngine, wire the /api/arb/backtest endpoint, and add the analytics
  tab to the Next.js dashboard. Run after /build-arb-layer and after collecting some
  resolved arb opportunities in SQLite.
slash_command: /run-backtest
---

# /run-backtest Workflow

Build the backtest engine and analytics tab.
**Prerequisite:** `/build-arb-layer` must be complete. At least a few resolved arb rows in SQLite (outcome != NULL).

---

## Step 1 — BacktestEngine

**Agent:** Backtest & Observability Engineer
**Read skill:** `backtest`

Create `src/apex/services/backtest_engine.py`:
- `BacktestEngine` dataclass with `run(lookback_days=90) -> BacktestResult`
- Reads from `store.get_resolved_arb_opportunities(since=...)`
- Computes: win_rate, avg_net_edge, total_pnl, Sharpe (annualised), edge_per_day series
- Tracks avg_hold_days, best_trade, worst_trade

---

## Step 2 — SQLiteStore methods

**Agent:** Backtest & Observability Engineer

Add to `src/apex/repositories/sqlite_store.py`:
- `get_resolved_arb_opportunities(since: str) -> list[ArbOpportunity]`
- Deserializes `settlement_flags` from JSON string
- Parses `detection_ts` and `resolution_ts` as `datetime` objects

---

## Step 3 — FastAPI endpoint

**Agent:** Backtest & Observability Engineer
**Read skill:** `backtest`

Add to `autopilot-local/backend/main.py`:
```python
@app.get("/api/arb/backtest")
async def get_backtest(lookback_days: int = 90):
    ...
```

Response shape:
```json
{
  "n_trades": 47,
  "win_rate": 0.63,
  "sharpe": 0.81,
  "total_pnl": 142.50,
  "avg_net_edge": 0.032,
  "avg_hold_days": 18.4,
  "edge_per_day": [["2025-02-01", 0.032], ...]
}
```

---

## Step 4 — Analytics tab (Next.js)

**Agent:** Frontend Engineer
**Read skill:** `backtest`

Create `autopilot-local/frontend/app/dashboard/analytics/BacktestTab.tsx`:
- 4 KPI tiles: Trades, Win Rate, Sharpe, Avg Edge
- Recharts `LineChart` of cumulative P&L over time
- `"use client"` directive
- Fetches from `/api/arb/backtest?lookback_days=90`

Integrate into existing `analytics/page.tsx`:
- Add a tab switcher: "Performance" | "Arb Backtest"
- Render `<BacktestTab />` when "Arb Backtest" is selected

---

## Step 5 — Seed test data (development only)

To populate resolved arb opportunities for testing:

```python
# scripts/seed_arb_backtest.py
import json
from datetime import datetime, timedelta
import random
from apex.core.config import get_settings
from apex.repositories.sqlite_store import SQLiteStore

settings = get_settings()
store    = SQLiteStore(settings.sqlite_path)

for i in range(50):
    det_ts = datetime.utcnow() - timedelta(days=random.randint(1, 90))
    res_ts = det_ts + timedelta(days=random.randint(3, 45))
    net_edge = random.uniform(0.02, 0.12)
    won = random.random() < 0.63  # 63% win rate per PRD target
    pnl = net_edge * 50 if won else -random.uniform(0.01, 0.05) * 50

    store._conn.execute("""
        INSERT OR IGNORE INTO arb_opportunities
        (id, kalshi_ticker, poly_market_id, question,
         kalshi_yes_ask, poly_no_ask, gross_spread, net_edge,
         settlement_match_score, settlement_flags,
         detection_ts, resolution_ts, outcome, pnl,
         volume_kalshi, volume_poly)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        f"seed_{i:04d}",
        f"KTEST-{i}",
        f"poly-{i}",
        f"Test market {i}",
        round(random.uniform(0.30, 0.60), 3),
        round(random.uniform(0.30, 0.55), 3),
        round(net_edge + 0.02, 3),
        round(net_edge, 3),
        round(random.uniform(0.5, 1.0), 2),
        "[]",
        det_ts.isoformat(),
        res_ts.isoformat(),
        "WIN" if won else "LOSS",
        round(pnl, 4),
        random.uniform(50_000, 500_000),
        random.uniform(50_000, 500_000),
    ))
store._conn.commit()
print(f"Seeded 50 resolved arb rows")
```

Run: `python scripts/seed_arb_backtest.py`

---

## Step 6 — Verify

```bash
curl "http://localhost:8000/api/arb/backtest?lookback_days=90"
```

Expected: JSON with `win_rate ≈ 0.63`, `sharpe ≈ 0.81`, `n_trades = 50` (if seeded).
