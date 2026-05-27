# APEX Autopilot Engine

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

**AI-governed, paper-only** autonomous execution for cross-market prediction arbitrage (Kalshi × Polymarket) with a 14-check risk stack and Bloomberg-style terminal.

Hackathon submissions: see **[HACKATHON.md](HACKATHON.md)** (Beyond Tomorrow Summit + Google Rapid Agent / Arize track).

### Judge demo (no API keys)

```bash
export DEMO_MODE=true
python scripts/seed_demo.py
uvicorn backend_api:app --port 8000
# Terminal: cd autopilot-local/frontend && npm run dev → /dashboard/arb-radar
```

Paper-trading autonomous execution engine implementing the APEX PRD v1.0 architecture:

1. **L0 Data Ingestion**: yfinance, Tradier (read-only), Alpaca account/market data, Polymarket signal adapters.
2. **L1 Finance Brain**: opportunity scoring with structured contracts and configurable intelligence weighting.
3. **L2 Multi-Agent Panel**: specialist analysis, bull/bear debate, judge synthesis, Dexter override.
4. **L3 Execution**: strict schema validation, ordered 14-check risk stack, preview/submit/monitor order flow.
5. **L4 Observability**: append-only audit log, P&L attribution, feedback memory, test-gate tracking.

## Quickstart

```bash
git clone git@github.com:aaravjj2/Autopilot.git
cd Autopilot
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp keys.env.example keys.env   # fill in API keys
cp .env.example .env             # tune feature flags
apex-engine
```

Secrets live in `keys.env` (gitignored). Integration repos go under `external/` — see [external/README.md](external/README.md).

## Production-mode integration enforcement

To enforce PRD-level integration readiness (paper-only broker + required credentials), enable strict mode:

```bash
export STRICT_INTEGRATIONS=true
apex-engine
```

When strict mode is on, startup fails if required broker/security conditions are missing.

## GitHub source integrations (PRD map)

Wire local checkouts for referenced repos via env vars (any subset):

```bash
export TRADINGAGENTS_REPO_PATH=/abs/path/TradingAgents
export DEXTER_REPO_PATH=/abs/path/dexter
export ANTHROPIC_FINANCIAL_SERVICES_REPO_PATH=/abs/path/financial-services
export MIROFISH_REPO_PATH=/abs/path/MiroFish
export DAILY_STOCK_ANALYSIS_REPO_PATH=/abs/path/daily_stock_analysis
export KRONOS_REPO_PATH=/abs/path/Kronos
export POLYMARKET_REPO_PATH=/abs/path/PolyMarket-MCP
export WHITMORELABS_REPO_PATH=/abs/path/polymarket-mcp
export ALPACA_MCP_REPO_PATH=/abs/path/alpaca-mcp-server
```

APEX records integration availability at startup in the audit log and can hard-fail in strict mode.

## Autotrading behavior

- `AUTOTRADE_ALL_APPROVED=true` (default): submit every approved proposal.
- `AUTOTRADE_ALL_APPROVED=false`: submit only `TOP_SYMBOLS_PER_DAY`.

## Run services

```bash
apex-scheduler          # or apex-autopilot (continuous)
apex-healthz            # :8088
apex-dashboard          # Streamlit ops :8501
```

### Full stack (APEX engine + copy-trading marketplace)

Uses `keys.env` + `.env` for Alpaca and API keys:

```bash
bash scripts/sync-copy-trading-env.sh
bash scripts/start-apex-stack.sh --restart
```

| Service | URL |
|---------|-----|
| APEX ops dashboard | http://localhost:8501 (sidebar → **Copy trading**) |
| Copy-trading UI | http://localhost:3000 |
| Copy-trading API | http://localhost:8000/api/health |
| APEX health | http://localhost:8088/healthz |

See [autopilot-local/README.md](autopilot-local/README.md) for the PRD app details.

## Notes

- **Paper trading only** is hard-enforced (`R01`) by account-mode and endpoint checks.
- **`DEMO_MODE=true`** seeds SQLite with synthetic arb opportunities and audit events for hackathon judges (no live venue keys).
- External adapters are interface-driven; if credentials are missing, engine degrades safely and refuses unsafe execution.
- Open source under **Apache-2.0** ([LICENSE](LICENSE)).
