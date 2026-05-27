# AGENTS.md

## Project Overview
APEX Autopilot Engine is an institutional‑grade, autonomous paper‑trading system that leverages the MarketMind AI engine to spot cross‑platform arbitrage opportunities across prediction markets such as Kalshi and Polymarket. The backend executes a disciplined L0‑L4 pipeline: ingestion, scoring, multi‑agent analysis, risk‑checked execution, and full observability. A Next.js‑based terminal provides a Bloomberg‑style audit stream, real‑time arb radar, and AI thesis streaming for operators.

## Architecture Map (L0‑L4)
- **L0 Ingestion**: `src/apex/layers/l0/ingestion.py`
- **L1 Finance Brain**: `src/apex/layers/l1/brain.py`
- **L2 Agent Panel**: `src/apex/layers/l2/agent_panel.py`
- **L3 Execution**: `src/apex/layers/l3/execution.py` & `src/apex/layers/l3/risk_checks.py`
- **L4 Observability**: `src/apex/layers/l4/observability.py`

## 20 Most Important Files
1. `src/apex/main.py` – engine factory assembling L0‑L4.
2. `src/apex/services/arb_engine.py` – core arbitrage scanner.
3. `src/apex/services/settlement_auditor.py` – resolves arb outcomes.
4. `src/apex/services/backtest_engine.py` – back‑tests arb performance.
5. `src/apex/layers/l0/ingestion.py` – market data ingestion.
6. `src/apex/layers/l1/brain.py` – scoring & contract structuring.
7. `src/apex/layers/l2/agent_panel.py` – multi‑agent decision panel.
8. `src/apex/layers/l3/execution.py` – order routing & dual‑leg submission.
9. `src/apex/layers/l3/risk_checks.py` – 14‑check risk gate.
10. `src/apex/layers/l4/observability.py` – audit logs & telemetry.
11. `src/apex/repositories/sqlite_store.py` – SQLite persistence layer.
12. `src/apex/integrations/hub.py` – external adapters (Polymarket, Alpaca).
13. `src/apex/core/config.py` – Pydantic settings.
14. `autopilot-local/backend/main.py` – FastAPI server for SSE streams.
15. `autopilot-local/frontend/app/page.tsx` – Next.js landing page.
16. `src/apex/services/engine.py` – high‑level orchestration.
17. `src/apex/services/pm_trading.py` – prediction‑market paper‑trading logic.
18. `src/apex/domain/models.py` – typed @dataclass domain contracts.
19. `src/apex/core/logging.py` – `get_logger(__name__)` helper.
20. `src/apex/core/retry.py` – `call_with_retries` wrapper for external APIs.

## Non‑Negotiable Rules
- **Paper Trading Only** – enforced by account‑mode checks (`R01`).
- **No Anthropic API** – all LLM calls go through `settings.get_llm_client()`.
- **APEX Conventions** – see `.agent/rules/apex-conventions.md`: Python 3.11+, `from __future__ import annotations`, full type hints, `get_logger(__name__)`, no bare `except:`.
- **DB Access** – only via `SQLiteStore`.
- **M01_PAPER_REQUIRED** must be first in every execution path.

## Current Roadmap Status Summary
The 10‑week master plan is mid‑stream: Weeks 1‑3 (high‑frequency ingestion, L2 agent hive, and cross‑asset integration) are complete; Week 4 (ML‑driven predictive arbitrage) is in production testing; Weeks 5‑7 (DeFi treasury management, VaR & Monte‑Carlo limits, autonomous execution state machine) are underway. The remaining weeks focus on multi‑agent orchestration, observability dashboards, and multi‑tenant fund features.

## How to Run Tests
- **Backend unit tests**: `python -m pytest tests/ -v`
- **Frontend E2E**: `cd autopilot-local/frontend && npx playwright test`

## Common Patterns (with one example each)
1. **API Retry Wrapper** – `apex.core.retry.call_with_retries()` is used for all external HTTP calls.
2. **Dataclass Domain Contracts** – functions return typed `@dataclass` objects such as `BacktestResult` instead of raw dicts.
3. **Pydantic Settings Engine** – `src/apex/core/config.py` defines a single `BaseSettings` class that all modules import.

## Known Issues / Gotchas (from logs)
- **yfinance 404 errors** – symbols like `SMH`, `SOXX`, `XSD`, and `SPY` sometimes lack fundamentals data, causing repeated `HTTP Error 404` entries.
- **Ollama connection refused** – the TradingAgents adapter frequently fails health checks (`http://localhost:11434`) when the Ollama service is not running.
- **Scheduler job duplication** – APScheduler logs show many "Adding job tentatively" messages; ensure jobs are registered only once after the scheduler starts.