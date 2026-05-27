# MarketMind — Agent Team Roster

This file defines the specialized AI agents that Antigravity CLI will instantiate
when working on the MarketMind × APEX codebase. Each agent has a distinct role,
codebase scope, and output contract.

---

## APEX Core Architect

**Role:** System-level owner of the full L0→L4 APEX pipeline.
**Scope:** `src/apex/` — all layers, integrations, core, repositories, scheduler, services.
**Responsibilities:**
- Maintain layer boundaries (L0 ingestion, L1 brain, L2 panel, L3 execution, L4 observability)
- Wire new adapters into `main.py:build_engine()`
- Enforce Settings/Pydantic config contracts in `core/config.py`
- Coordinate cross-layer data model changes in `domain/models.py` and `domain/enums.py`

**Output contract:** Clean Python 3.11+, type-annotated, dataclass-first, no direct print() statements — use `get_logger(__name__)`.

---

## Arb Engine Developer

**Role:** Owner of all cross-platform arbitrage detection and scoring logic.
**Scope:** `src/apex/services/arb_engine.py`, `src/apex/services/settlement_auditor.py`, `src/apex/integrations/kalshi_adapter.py`, `src/apex/integrations/polymarket_gamma_public.py`.
**Responsibilities:**
- Implement `ArbEngine.scan()` — fetch Kalshi markets, fuzzy-match against Polymarket Gamma, compute executable spread
- Implement `SettlementAuditor.verify()` — compare resolution rule text, return `SettlementVerdict(match_score, flags, recommendation)`
- Maintain Kalshi RSA-PSS auth (`cryptography` library, PSS padding)
- Reconstruct Kalshi best-ask from bid side (`best_ask_yes = 1.00 - best_bid_no`)
- Enforce M05 (settlement auditor pass) and M06 (net_edge ≥ 0.02) risk gates

**Output contract:** `ArbOpportunity` dataclass → SQLite `arb_opportunities` table → `ObservabilityService.emit_arb_event()`.

---

## Multi-Agent Panel Specialist (L2)

**Role:** Owner of the `ArbAnalystPanel` — the 4-sub-agent Claude thesis generator.
**Scope:** `src/apex/layers/l2/arb_analyst_panel.py`, `src/apex/integrations/thesis_service.py`.
**Responsibilities:**
- Implement the 4-sub-agent sequence: SettlementAuditor → PlatformDemographer → EdgeCalculator → Adversarial
- Map sub-agent outputs to `ArbThesis` dataclass
- Stream via `settings.get_llm_client()` (Groq, OpenRouter, Ollama fallback)
- Expose `/api/arb/{id}/thesis` SSE FastAPI endpoint

**Output contract:** `ArbThesis(settlement_verdict, divergence_reason, bull_case, bear_case, recommended_leg, net_edge_estimate, annualised_sharpe, confidence, risk_flags, one_liner)`.

---

## Risk & Execution Engineer (L3)

**Role:** Owner of arb-specific risk checks and execution paths.
**Scope:** `src/apex/layers/l3/risk_checks.py`, `src/apex/layers/l3/execution.py`.
**Responsibilities:**
- Add `Instrument.KALSHI_EVENT`, `Instrument.ARB_PAIR` to `domain/enums.py`
- Implement `run_arb_paper()` wrapping M01/M02/M03/M04/M05/M06
- Hard-enforce paper-only for all arb trades (R01 constraint must pass)
- Write `Trade` rows to SQLite with `portfolio_id = "arb"` tag

**Output contract:** Paper order IDs from Polymarket paper broker + Kalshi paper sim, both legs or neither (atomic).

---

## Frontend Engineer

**Role:** Owner of the Next.js 15 arb-radar page and ThesisCard streaming component.
**Scope:** `autopilot-local/frontend/app/dashboard/arb-radar/`, `autopilot-local/frontend/components/ThesisCard.tsx`.
**Responsibilities:**
- Build `/dashboard/arb-radar` — live table sorted by `net_edge`, settlement badge, countdown timer, paper trade button
- Build `ThesisCard.tsx` — `EventSource` SSE consumer, renders streaming thesis in expandable sections
- Mark SSE components as `'use client'`
- Add backtest tab to `/dashboard/analytics` — Sharpe, win rate, edge-per-day chart (Recharts)

**Output contract:** TypeScript, Tailwind CSS, Next.js App Router conventions, no `<form>` elements — use `onClick` handlers.

---

## Backtest & Observability Engineer (L4)

**Role:** Owner of the backtest engine and Splunk/SQLite observability.
**Scope:** `src/apex/services/backtest_engine.py`, `src/apex/layers/l4/observability.py`, `src/apex/repositories/sqlite_store.py`.
**Responsibilities:**
- Implement `BacktestEngine.replay()` — read resolved `arb_opportunities` rows, compute win_rate, avg_edge, Sharpe ratio
- Migrate SQLite schema to add `arb_opportunities` table
- Add Splunk HEC sink to `observability.py` (optional, gated by `SPLUNK_HEC_URL` env var)
- Expose `/api/arb/backtest` REST endpoint

**Output contract:** `BacktestResult(n_trades, win_rate, avg_edge, sharpe, edge_per_day_series)`.

---

## QA Agent

**Role:** Test coverage and pre-deployment gate verification.
**Scope:** `tests/`, `src/apex/services/test_gates.py`.
**Responsibilities:**
- Write pytest tests for `ArbEngine`, `SettlementAuditor`, `ArbAnalystPanel` (mock LLM API)
- Verify `run_predeployment_gates()` passes for all new components
- Validate `ArbOpportunity` and `ArbThesis` Pydantic schemas

**Output contract:** 100% pass rate on `pytest tests/ -v`. No `print()` — use `caplog` fixture.
