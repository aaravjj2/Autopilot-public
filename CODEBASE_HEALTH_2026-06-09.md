# Codebase Health & Environment Report
**Generated:** 2026-06-09T14:56 UTC
**Overall Status: HEALTHY ✅** (with known issues tracked)
**Cycle:** #660+ iterations, 131 commits, 33 tags

---

## 1. Environment

| Component | Status | Details |
|-----------|--------|---------|
| **OS** | ✅ | WSL (Ubuntu on Windows) — `/dev/sdd` ext4 |
| **Python** | ✅ | 3.13.12 (miniconda3 — system default) |
| **Node** | ✅ | v22.22.1 / npm 10.9.4 (via nvm) |
| **Disk** | ✅ | 1,007G total, 213G used (23%), **744G free** |
| **RAM** | ✅ | 23Gi total, 9.4Gi used, **13Gi available** |
| **Virtual Env** | ✅ | `.venv/` — 278 packages, `pip check` clean |
| **Linters** | ✅ | **INSTALLED** — ruff 0.15.16, mypy 2.1.0, pylint 4.0.5 in .venv |
| **Playwright** | ✅ | v1.60.0, chromium-1223 cached (browsers available for E2E) |

**Linters upgrade note:** Cycle `cycle-20260609-101605` installed linters in .venv. System pip still has older versions (ruff 0.8.4, mypy 1.14.0) but .venv is the active environment.

---

## 2. Git State

| Metric | Value |
|--------|-------|
| **Branch** | `main` — ahead of `origin/main` by **12 commits** |
| **Commits** | 131 total on main |
| **Tags** | 33 tags (latest: `cycle-20260609-143000-final`) |
| **Remote** | `https://github.com/aaravjj2/Autopilot-public.git` — **PAT removed** ✅ (no credentials) |
| **Uncommitted** | Working tree **clean** — no modified or untracked files |
| **Submodules** | 9 external repos — **all initialized and checked out** |
| **Stashed** | Empty — nothing stashed |

### Unsynced commits (12 ahead, not in remote)
```
fa35f01 docs(report): final cycle report v10 — ~660 iterations, 131 commits, 33 tags
4662eba docs(report): update cycle final report with verified push failure message
a9729f6 feat(data): restructure training corpus with real arb opportunities and world cup predictions
38469c3 feat(data): add kalshi market ticks for NBA 3PT and WTA tennis markets
6c35224 docs(health): update codebase health report with current stats and issue tracking
7881853 style(lint): cleanup imports and fix bare f-string in autopilot-continuous.py
57f81e3 chore(logs): add cycle and error report logs from recent runs
57f43b2 fix(lint): add tests/__init__.py, fix test imports, remove dead code, run ruff
e945916 docs(report): final cycle report v9 — ~653 iterations, 123 commits, 33 tags
53e995e feat(data): restructure training corpus with real arb opportunities
e794bb2 fix(cleanup): remove dead gemini CLI code, add opencode probe, log bare exception handlers
69f34ef fix(security): remove PAT from remote URL, untrack .state/ secrets, create .gitmodules
```

### Git push BLOCKED 🚫
`fatal: could not read Username for 'https://github.com': No such device or address`
PAT was removed from remote URL (security fix in commit `69f34ef`) but no credential helper was configured. 12 commits and 33 tags exist locally only, not backed up to remote. **This is the highest-priority blocker.**

---

## 3. Running Services

| Service | PID | Port | Status | Uptime |
|---------|-----|------|--------|--------|
| **Backend API** (FastAPI) | 285356 | :8000 | ✅ HEALTHY — HTTP 200 (0.20s) | ~31h (since Jun 8) |
| **Frontend** (Next.js v15.5.18) | 294555 | :3000 | ✅ HEALTHY — HTML loaded | ~31h (since Jun 8) |
| **Loop Daemon** (autopilot-continuous.py) | 257711 | — | ✅ RUNNING | ~30h (since Jun 8) |

### Duplicate process
PID **590137** — runs `.venv/bin/python api/app.py --host 0.0.0.0 --port 8000` (root-owned). Port 8000 is already held by uvicorn (285356). This is a **stale process from another project** (`Apex-Terminal/FinceptTerminal`). Should be killed to free resources — but it's root-owned, so `sudo kill 590137` would be needed.

---

## 4. Source Code

| Metric | Count |
|--------|-------|
| **Python source files** | 168+ in `src/apex/` |
| **Module packages** | 22 (agents, analytics, brain, cache, core, cross_asset, dashboard, defi, demo, domain, execution, fund, grpc, ingestion, integrations, layers, ml, monitor, monitoring, observability, repositories, risk, scheduler, security, services, streaming) |
| **Test files** | 40+ in `tests/` (with 414 test cases) |
| **Top-level scripts** | 7 (autopilot.py, backend_api.py, autopilot-continuous.py, migrate_consolidate_db.py, backup_db.py, build_apex_pdf.py, run_discord_bot.py) |
| **All Python files syntax-checked** | ✅ All parse clean |

### Architecture
- **L0 Ingestion** — Kalshi polling, Polymarket adapter, YFinance
- **L1 Brain** — FinanceBrain (knowledge cards), QuantEngine (fractional Kelly sizing)
- **L2 Agent Panel** — TradingAgents (submodule, DEGRADED — Ollama not running)
- **L3 Execution** — Risk gate (14 checks), paper-trade enforcement
- **L4 Observability** — Audit log, SSE, Prometheus wiring
- **Frontend** — Next.js dashboard at `autopilot-local/frontend/`
- **ML Pipeline** — Arb edge model training via self-improvement loop

---

## 5. Dependencies

| Group | Status | Notes |
|-------|--------|-------|
| **Core** (pyproject.toml) | ✅ 27 packages | FastAPI 0.136.1, Pydantic 2.13.4, SQLModel 0.0.38, APScheduler 3.11.2, pandas 2.3.3, numpy 2.4.5, yfinance 0.2.66 |
| **Dev** | ✅ Installed | pytest 8.4.2, pytest-asyncio 1.4.0, pytest-timeout 2.4.0, pytest-cov, pytest-playwright 0.8.0 |
| **Agents** | ✅ Installed | langgraph, langchain-openai, openai |
| **Linters** | ✅ **Installed** | **RESOLVED** — ruff 0.15.16, mypy 2.1.0, pylint 4.0.5 in .venv |

`pip check` — No broken requirements found.

---

## 6. Test Suite

| Metric | Value |
|--------|-------|
| **Tests collected** | **414** |
| **Passed** | **394** (100% pass rate) |
| **Failed** | **0** |
| **Skipped** | **20** (Playwright E2E — depends on browser runtime availability) |
| **Smoke tests** | **10/10 passed** in **9.56s** |
| **Playwright browsers** | ✅ Chromium-1223 cached at `~/.cache/ms-playwright/` |

### Smoke Tests (10 critical-path) — all pass ✅
- `test_arb_engine.py::test_topics_compatible_blocks_cross_topic_false_positives`
- `test_auth_api.py::test_reads_are_public`
- `test_brain_conviction.py::test_trend_score_bullish`
- `test_dashboard_health.py::test_llm_route_ok_in_heuristic_mode`
- `test_dashboard_health.py::test_llm_route_ok_when_groq_key_present`
- `test_execution.py::test_execution_rejects_below_conviction_floor`
- `test_finance_brain.py::test_knowledge_cards_have_unique_ids_and_content`
- `test_quant_engine.py::test_fractional_kelly_produces_valid_sizes`
- `test_risk_checks.py::test_r01_rejects_live_endpoint`
- `test_scheduler_jobs.py::test_register_jobs_schedule_matches_callbacks`

**Warnings:** 1 StarletteDeprecationWarning (upstream, non-blocking). ChromaDB Pydantic warnings also present but filtered in pytest.ini.

---

## 7. Data & ML Models

| Metric | Value |
|--------|-------|
| **Database total size** | ~60 MB |
| `data/audit.db` | **18 MB** — main audit database |
| `data/signal_quality.db` | 20 KB |
| `data/marketmind.db` | **0 bytes** (empty — likely unused) |
| `data/discord_trades.db` | 12 KB |
| **Arb opportunities** | **358** (via API health endpoint) |
| **Proposals** | **13** |
| **Positions** | **0** (paper mode) |
| **Active model** | `20260608T191239Z` — **92.17% accuracy** |
| **Candidate models** | **328+** trained |
| **Training corpus** | `data/training/corpus.jsonl` — updated Jun 9 (179KB) |
| **Kalshi ticks** | `data/kalshi_ticks.jsonl` — updated Jun 9 (352KB) |
| **Self-improvement loop** | Enabled (but loop currently disabled in scheduler) |
| **Data freshness** | ⚠️ Last cache update ~38h ago (`is_stale: true`) |

---

## 8. Backend API Health

```json
{
    "status": "healthy",
    "timestamp": "2026-06-09T14:56:01Z",
    "last_cache_update": "2026-06-08T00:40:32Z",
    "is_stale": true,
    "alpaca_connected": true,
    "yfinance_ok": true,
    "opportunities": 358,
    "proposals": 13,
    "positions": 0,
    "ml": {
        "self_improvement_enabled": true,
        "active_model": { "version": "20260608T191239Z", "accuracy": 0.9217 },
        "backtest_90d": { "n_trades": 16, "win_rate": 0.5, "sharpe": 3.211, "total_pnl": 18.2 }
    },
    "kalshi_ws": { "connected": true, "stale": true },
    "scheduler": { "mode": "in_process_loops", "status": "ok" }
}
```

---

## 9. Known Issues (Active)

| # | Severity | Issue | Status |
|---|----------|-------|--------|
| 1 | 🔴 **Critical** | **Git push blocked** — PAT removed, no credential helper. 12 commits + 33 tags local only, not in remote. | Active — `69f34ef` fixed PAT exposure but broke push |
| 2 | 🟡 **Medium** | **Data stale** — Last cache update 38h+ ago. Kalshi tick data and arb opportunities may be outdated. | Active — needs cache refresh |
| 3 | 🟡 **Medium** | **LLM routing all broken** — Groq 401, OpenCode Zen 429 → deterministic fallback only. No AI-powered analysis/planning. | Active — persistent across many cycles |
| 4 | 🟡 **Medium** | **Ollama not running** — TradingAgents health-check fails; L2 Agent Panel DEGRADED. | Active |
| 5 | 🟢 **Low** | **Duplicate backend process** — PID 590137 (root-owned, from Apex-Terminal project) runs `api/app.py` on port 8000 but port is held by uvicorn 285356. | Active — `sudo kill 590137` needed |
| 6 | 🟢 **Low** | **marketmind.db empty** — 0 bytes, likely unused. | Active |
| 7 | 🟢 **Low** | **Chromadb Pydantic / Starlette warnings** — Upstream deprecation warnings. Non-blocking. | Active |

---

## 10. Issues Resolved Since Last Report

| Issue | Previous State | Current State |
|-------|---------------|---------------|
| **Linters not installed** | 🔴 pylint, ruff, mypy missing from venv | ✅ **INSTALLED** — ruff 0.15.16, mypy 2.1.0, pylint 4.0.5 in .venv |
| **Test stability** | Stable in v9 | ✅ **Still stable** — 414/414 known, 394 pass, 0 fail, 20 skip |
| **Smoke tests** | 10/10 in 4.90s (v9) | ✅ **Pass** — 10/10 in 9.56s (slightly slower, still healthy) |
| **Uncommitted changes** | 3 modified + untracked files | ✅ **Working tree clean** — all changes committed |

---

## 11. Recommendations (Priority Order)

1. 🔴 **Fix git push** — Configure `gh auth login` with a token or set `git credential.helper` to restore push capability. 12 commits and 33 tags are local-only — one disk failure loses everything.
2. 🟡 **Refresh data** — Trigger Kalshi poll cycle to update 38h-stale cache. Either trigger arb_scan_loop manually or restart scheduler with `self_improvement_loop` enabled.
3. 🟡 **Revive LLM routing** — Fix Groq key (expired 401) or start Ollama locally. Currently stuck on deterministic fallback only — no AI analysis available.
4. 🟢 **Kill stale process** — `sudo kill 590137` to remove duplicate root-owned process hogging resources.
5. 🟢 **Daily push cadence** — Once push is fixed, establish regular commit+push schedule to prevent large unsynced commit piles.

---

## 12. Summary

```
Backend API   :8000  ===  HEALTHY ✅  (uvicorn PID 285356)
Frontend      :3000  ===  HEALTHY ✅  (Next.js v15.5.18)
Loop Daemon         ===  HEALTHY ✅  (autopilot-continuous PID 257711)
Tests (414)         ===  394 PASS ✅  0 FAIL  20 SKIP
Smoke (10)          ===  10/10 PASS ✅
Git (origin/main)   ===  12 ahead, PUSH BLOCKED 🚫
Linters             ===  INSTALLED ✅  (ruff, mypy, pylint in .venv)
Data staleness      ===  38h stale ⚠️
LLM routing         ===  BROKEN 🔴  (deterministic fallback only)
Disk / RAM          ===  HEALTHY ✅  (744G free / 13Gi available)
```
