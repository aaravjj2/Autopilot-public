# Autopilot Local — Product Requirements Document

**Version:** 1.0  
**Status:** Draft  
**Scope:** Personal-use, local-only copy-trading app powered by Alpaca Paper Trading  

---

## 1. Overview

Autopilot Local is a single-user, locally-hosted investment copy-trading application inspired by joinautopilot.com. The user browses a curated marketplace of portfolios (political trackers, hedge fund mirrors, influencer picks), selects one or more to follow, and the app automatically mirrors trades into their Alpaca paper trading account in real time.

No real money moves. No cloud infrastructure. No auth. Everything runs on localhost.

---

## 2. Goals

- Replicate the core Autopilot product loop for personal use: browse → follow → auto-trade
- Run entirely on localhost with zero external services beyond public APIs
- Use Alpaca Paper Trading as the sole brokerage layer (no real money, no SEC compliance needed)
- Keep the stack minimal: Next.js frontend + FastAPI backend + SQLite database
- Support the most compelling Autopilot portfolio categories: political disclosures, 13F hedge fund trackers, and curated thematic picks

---

## 3. Out of Scope

- Real money trading or live brokerage connections
- Multi-user support, authentication, or session management
- Cloud deployment (Vercel, Railway, GCP)
- Mobile apps
- Pilot creator onboarding (no public portfolio submission flow)
- SEC registration, RIA compliance, or KYC/AML
- Fan-out trade execution across multiple accounts
- Payment processing or subscription billing

---

## 4. User

Single user: the developer/owner running the app locally. All configuration is via `.env.local`. The app renders in a browser at `localhost:3000`.

---

## 5. Architecture

### 5.1 Stack

| Layer | Technology | Notes |
|---|---|---|
| Frontend | Next.js 15 (App Router) + TypeScript + Tailwind CSS | localhost:3000 |
| Backend | FastAPI (Python 3.11+) | localhost:8000 |
| Database | SQLite via SQLModel | Single `autopilot.db` file, gitignored |
| Scheduler | APScheduler (in-process) | Refreshes data every 30 min |
| Charts | Recharts | Portfolio performance time-series |
| Brokerage | Alpaca Paper Trading API | Paper orders only |
| Market data | yfinance | OHLCV + returns calculation |
| Congressional data | Quiver Quantitative API (free tier) | Congress + Senate endpoints |
| Institutional data | SEC EDGAR REST API | 13F filings, no auth required |
| Real-time quotes | Alpaca WebSocket stream | Live P&L on dashboard |

### 5.2 Folder Structure

```
autopilot-local/
  frontend/
    app/
      page.tsx                  # marketplace (root)
      portfolio/[id]/page.tsx   # portfolio detail + follow toggle
      dashboard/page.tsx        # user's P&L + open positions
    components/
      PortfolioCard.tsx
      PerformanceChart.tsx
      HoldingsTable.tsx
      PositionRow.tsx
    lib/
      api.ts                    # typed fetch wrappers → localhost:8000
  backend/
    main.py                     # FastAPI app + CORS
    alpaca.py                   # Alpaca REST + WebSocket client
    portfolios.py               # portfolio definitions + follow logic
    sync.py                     # trade mirroring engine
    scheduler.py                # APScheduler jobs
    db.py                       # SQLModel models + session
    data/
      congress.py               # Quiver Quantitative fetch + parse
      sec_13f.py                # EDGAR 13F fetch + parse
      performance.py            # yfinance returns + Sharpe calc
  .env.local                    # API keys — gitignored
  autopilot.db                  # SQLite data — gitignored
  start.sh                      # starts both servers concurrently
  README.md
```

### 5.3 Environment Variables

```
ALPACA_API_KEY=...
ALPACA_API_SECRET=...
ALPACA_BASE_URL=https://paper-api.alpaca.markets
ALPACA_DATA_URL=https://data.alpaca.markets
QUIVER_API_KEY=...
```

---

## 6. Data Models

### Portfolio

```
id            TEXT PRIMARY KEY    # slug, e.g. "pelosi-tracker"
name          TEXT
description   TEXT
category      TEXT                # "political" | "hedge-fund" | "thematic"
pilot_name    TEXT                # display name of the strategy creator
is_following  BOOLEAN DEFAULT 0
created_at    DATETIME
updated_at    DATETIME
```

### Holding

```
id            INTEGER PRIMARY KEY AUTOINCREMENT
portfolio_id  TEXT FK → Portfolio
ticker        TEXT
weight        FLOAT               # 0.0–1.0, portfolio allocation
shares        FLOAT               # computed from weight × account value
last_updated  DATETIME
```

### Trade

```
id                INTEGER PRIMARY KEY AUTOINCREMENT
portfolio_id      TEXT FK → Portfolio
ticker            TEXT
side              TEXT            # "buy" | "sell"
qty               FLOAT
price             FLOAT
alpaca_order_id   TEXT
status            TEXT            # "pending" | "filled" | "failed"
executed_at       DATETIME
```

### PerformanceSnapshot

```
id            INTEGER PRIMARY KEY AUTOINCREMENT
portfolio_id  TEXT FK → Portfolio
date          DATE
value_usd     FLOAT               # portfolio NAV on this date
return_pct    FLOAT               # cumulative return from inception
```

### Position (user's live Alpaca positions)

```
ticker        TEXT PRIMARY KEY
qty           FLOAT
avg_entry     FLOAT
current_price FLOAT
unrealized_pl FLOAT
portfolio_id  TEXT                # which followed portfolio placed this
```

---

## 7. Portfolio Definitions

Portfolios are defined as code in `backend/portfolios.py` and seeded into SQLite on first run. Initial set:

### Political trackers (via Quiver Quantitative)

| ID | Name | Source |
|---|---|---|
| `pelosi-tracker` | Pelosi Tracker | Quiver `/congress` filtered by Nancy Pelosi |
| `trump-portfolio` | Trump Stock Portfolio | Quiver `/congress` filtered by Trump family disclosures |
| `senate-buys` | Senate Best Buys | Top bought tickers across all Senate disclosures, last 90 days |

### Hedge fund mirrors (via SEC EDGAR 13F)

| ID | Name | CIK |
|---|---|---|
| `simons-tracker` | Jim Simons Tracker | Renaissance Technologies CIK |
| `burry-tracker` | Burry Tracker | Scion Asset Management CIK |
| `dalio-tracker` | Dalio Tracker | Bridgewater Associates CIK |

### Thematic (hardcoded or AI-generated, refreshed manually)

| ID | Name | Logic |
|---|---|---|
| `inverse-cramer` | Inverse Cramer | Inverse of CNBC Jim Cramer buy recommendations (manually curated) |
| `ai-basket` | AI Picks | Top 10 AI/ML-adjacent holdings across all tracked 13Fs |

---

## 8. Features

### 8.1 Portfolio Marketplace (root page `/`)

- Grid of portfolio cards, each showing:
  - Portfolio name + pilot name
  - Category badge (political / hedge-fund / thematic)
  - Return percentage for selected period
  - Assets under management equivalent (simulated, based on $100k paper account)
  - "Following" toggle
- Time period selector: 1W / 1M / 3M / 6M / 1Y
- Sort by: top performers / most popular / newest
- Filter by: category

### 8.2 Portfolio Detail Page (`/portfolio/[id]`)

- Performance chart (line chart, cumulative return vs S&P 500 benchmark)
- Current holdings table: ticker, weight %, shares, current price, value
- Recent trades log: date, ticker, side, qty, fill price
- Follow / unfollow toggle
  - On follow: calls `POST /api/portfolios/{id}/follow` → backend calculates position sizes → submits paper orders to Alpaca
  - On unfollow: calls `DELETE /api/portfolios/{id}/follow` → backend closes all positions for this portfolio in Alpaca

### 8.3 Dashboard (`/dashboard`)

- Account summary bar: total paper account value, total unrealized P&L, cash available
- Live P&L updates via SSE (`GET /api/stream/pnl`) fed by Alpaca WebSocket quote stream
- Followed portfolios cards: mini chart, return since followed, current value
- All open positions table: ticker, qty, entry price, current price, P&L, which portfolio
- Trade history: last 50 executed orders

### 8.4 Settings (modal or `/settings`)

- Display Alpaca paper account connection status (ping `GET /api/health`)
- Manual data refresh button (triggers all scheduler jobs immediately)
- Display last refresh timestamp per portfolio

---

## 9. Backend API Routes

### Portfolios

```
GET  /api/portfolios                  list all portfolios with current perf data
GET  /api/portfolios/{id}             portfolio detail + holdings + recent trades
POST /api/portfolios/{id}/follow      follow a portfolio (place paper trades)
DELETE /api/portfolios/{id}/follow    unfollow (close all positions for this portfolio)
```

### Dashboard

```
GET  /api/dashboard                   account summary + all positions
GET  /api/stream/pnl                  SSE stream: live quote updates for open positions
```

### Data

```
POST /api/refresh/all                 trigger all data refresh jobs
POST /api/refresh/{portfolio_id}      trigger refresh for one portfolio
GET  /api/health                      alpaca connection status + last refresh times
```

---

## 10. Data Refresh Logic

All refresh jobs run in APScheduler, in-process with FastAPI.

### Political tracker refresh (every 30 min during market hours)

1. Call Quiver `/congress` endpoint, filter by relevant politician
2. Parse latest disclosure transactions (within last 30 days)
3. Compute portfolio weights from transaction sizes
4. Compare against current holdings in SQLite
5. If holdings changed: submit Alpaca paper orders to rebalance
6. Snapshot new performance value

### 13F hedge fund refresh (daily, 6am)

1. Call SEC EDGAR EFTS API for latest 13F filing by CIK
2. Parse XML holdings list
3. Compute weight from market value per position
4. Compare against stored holdings, rebalance if following
5. Snapshot performance

### Performance snapshot (daily, 6am)

1. For each portfolio, pull current holdings
2. Use yfinance to get today's close prices
3. Compute NAV = sum(shares × price) per portfolio
4. Calculate cumulative return since portfolio inception
5. Write PerformanceSnapshot row to SQLite

### Live quote stream (while app is open)

1. On startup, connect Alpaca WebSocket to `wss://stream.data.alpaca.markets/v2/iex`
2. Subscribe to quotes for all tickers in open positions
3. Push updated prices via SSE to frontend dashboard

---

## 11. Trade Mirroring Logic

When the user follows a portfolio:

1. Read portfolio holdings from SQLite (weights sum to 1.0)
2. Get available cash from Alpaca paper account
3. For each holding: `shares = floor((weight × account_value) / current_price)`
4. Check existing Alpaca positions — only trade the delta (don't double-buy)
5. Submit market orders via Alpaca REST API
6. Poll order status until filled or timeout (30s)
7. Write Trade rows to SQLite with Alpaca order IDs and fill prices

When a portfolio's holdings change (detected on refresh):
1. Compute new target positions
2. Compute delta vs current Alpaca positions
3. Submit rebalance orders (sell excess, buy new)

---

## 12. Performance Calculations

Using yfinance for historical data and returns math done in Python:

- Cumulative return: `(current_value - inception_value) / inception_value`
- Period return (1W/1M etc): slice PerformanceSnapshot table by date range
- Benchmark: pull SPY daily closes for same period, compute same return
- Sharpe ratio (displayed on portfolio detail): `(annualized_return - 0.05) / annualized_std`

---

## 13. Frontend Component Map

```
app/page.tsx (marketplace)
  └── <PortfolioGrid>
        └── <PortfolioCard>          name, return %, AUM, follow toggle
              └── <MiniChart>        7-day sparkline

app/portfolio/[id]/page.tsx
  ├── <PerformanceChart>             recharts line chart, period selector
  ├── <HoldingsTable>                ticker, weight, shares, value
  ├── <TradeLog>                     recent fills
  └── <FollowButton>                 POST/DELETE /api/portfolios/{id}/follow

app/dashboard/page.tsx
  ├── <AccountSummary>               total value, P&L, cash
  ├── <FollowedPortfolios>           mini cards for each followed portfolio
  └── <PositionsTable>               all open positions + live P&L via SSE
```

---

## 14. Start Script

`start.sh`:
```bash
#!/bin/bash
# Start FastAPI backend
cd backend && uvicorn main:app --reload --port 8000 &

# Start Next.js frontend
cd frontend && npm run dev &

wait
```

Or use `concurrently` from root `package.json`:
```json
{
  "scripts": {
    "dev": "concurrently \"cd backend && uvicorn main:app --reload --port 8000\" \"cd frontend && npm run dev\""
  }
}
```

---

## 15. Success Criteria

- [ ] Marketplace renders all 8 seed portfolios with performance data
- [ ] Following a portfolio submits real paper orders to Alpaca and they appear as fills
- [ ] Dashboard shows live P&L updating in real time via SSE
- [ ] Political tracker data refreshes from Quiver Quantitative on schedule
- [ ] 13F hedge fund data parses from SEC EDGAR correctly
- [ ] Unfollowing a portfolio closes all associated Alpaca positions
- [ ] `start.sh` launches the full app with one command
- [ ] `.env.local` and `autopilot.db` are gitignored
