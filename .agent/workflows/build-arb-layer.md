---
name: build-arb-layer
description: >
  Full scaffold of the MarketMind arb detection pipeline. Runs the Arb Engine Developer
  and APEX Core Architect agents in sequence to create all arb-layer files from scratch.
  Use this when starting the MarketMind feature from zero.
slash_command: /build-arb-layer
---

# /build-arb-layer Workflow

Scaffold the full arb detection pipeline for MarketMind. This workflow creates all
missing files in the correct dependency order.

---

## Step 1 — Domain model additions

**Agent:** APEX Core Architect
**Read skill:** `apex-dev`

Add to `src/apex/domain/models.py`:
- `ArbOpportunity` dataclass (see arb-engine skill)
- `ArbThesis` dataclass (see thesis-card skill)
- `BacktestResult` dataclass (see backtest skill)
- `SettlementVerdict` dataclass (see arb-engine skill)

Add to `src/apex/domain/enums.py`:
- `Instrument.KALSHI_EVENT`
- `Instrument.ARB_PAIR`
- `EventType.ARB_DETECTED`, `ARB_RISK_PASSED`, `ARB_RISK_FAILED`, `ARB_PAPER_SUBMITTED`, `ARB_RESOLVED`

Add to `src/apex/core/config.py`:
- `kalshi_access_key`, `kalshi_private_key_path`, `kalshi_min_volume_24h`
- `arb_min_net_edge`, `arb_scan_interval_minutes`
- `splunk_hec_url` (optional, gated)

---

## Step 2 — Kalshi adapter

**Agent:** Arb Engine Developer
**Read skill:** `kalshi-api`

Create `src/apex/integrations/kalshi_adapter.py`:
- `KalshiAuth` class with RSA-PSS signing
- `KalshiMarket` dataclass
- `KalshiEventClient` class with `get_macro_markets(min_volume)`
- `reconstruct_asks()` helper
- `compute_net_edge()` helper

---

## Step 3 — Polymarket enrichment

**Agent:** Arb Engine Developer
**Read skill:** `polymarket`

Extend `src/apex/integrations/polymarket_gamma_public.py`:
- Add `enrich_for_arb=False` param to `fetch_active_liquid_markets()`
- Add `parse_outcome_prices()` helper
- Add `get_best_ask_no()` CLOB helper (optional, gated by `USE_CLOB_ORDERBOOK` env var)

---

## Step 4 — Settlement auditor

**Agent:** Arb Engine Developer
**Read skill:** `arb-engine`

Create `src/apex/services/settlement_auditor.py`:
- `SettlementAuditor` dataclass with `verify(kalshi_title, poly_question) -> SettlementVerdict`
- Checks: timing alignment, source divergence, threshold mismatch, entertainment/subjective risk
- Returns `SettlementVerdict(match_score, flags, recommendation)`

---

## Step 5 — Arb engine

**Agent:** Arb Engine Developer
**Read skill:** `arb-engine`

Create `src/apex/services/arb_engine.py`:
- `ArbEngine` dataclass with `scan() -> list[ArbOpportunity]`
- Fuzzy matching via `difflib.SequenceMatcher` (threshold: 0.72)
- Net edge computation with Kalshi 7% fee
- Calls SettlementAuditor for each match
- Filters by `settings.arb_min_net_edge`

---

## Step 6 — SQLite migration

**Agent:** Backtest & Observability Engineer
**Read skill:** `apex-dev`

Add to `SQLiteStore._migrate()` in `src/apex/repositories/sqlite_store.py`:
- `arb_opportunities` table (full schema from arb-engine skill)
- `upsert_arb_opportunity()` method
- `get_arb_opportunity(id)` method
- `get_recent_arb_opportunities(limit, min_edge)` method
- `get_resolved_arb_opportunities(since)` method

---

## Step 7 — Risk checks (M05, M06)

**Agent:** Risk & Execution Engineer
**Read skill:** `risk-stack`

Add to `src/apex/layers/l3/risk_checks.py`:
- `ArbRiskCheckResult` class
- `run_arb_paper(opp, settings) -> ArbRiskCheckResult` function
- M01 through M06 check functions

Add to `src/apex/layers/l3/execution.py`:
- `submit_arb_paper_orders(opp, stake_usd) -> tuple[str|None, str|None]`

---

## Step 8 — Scheduler job

**Agent:** APEX Core Architect
**Read skill:** `apex-dev`

Add to `src/apex/scheduler/jobs.py`:
- `("arb_scan", 9, 25, None)` to SCHEDULE list
- `("arb_scan_intraday", 11, 0, None)`
- `("arb_scan_intraday", 13, 0, None)`
- `arb_scan(engine: ApexEngine)` job function

---

## Step 9 — Wire into build_engine()

**Agent:** APEX Core Architect
**Read skill:** `apex-dev`

Edit `src/apex/main.py:build_engine()`:
- Import `KalshiEventClient`
- Create `kalshi_client = KalshiEventClient(settings) if settings.kalshi_access_key else None`
- Pass to integration registry

---

## Step 10 — Verification

Run:
```bash
python -c "from apex.services.arb_engine import ArbEngine; print('OK')"
python -c "from apex.services.settlement_auditor import SettlementAuditor; print('OK')"
python -m pytest tests/test_arb_engine.py -v
```

Expected: all imports succeed, tests pass.
