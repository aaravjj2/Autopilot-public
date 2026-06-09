# Codebase Health & Environment Report
**Generated:** 2026-06-09T14:06 UTC
**Overall Status: HEALTHY ✅** (with known issues tracked)

---

## 1. Environment

| Component | Status | Details |
|-----------|--------|---------|
| **OS** | ✅ | WSL (Ubuntu on Windows) — `/dev/sdd` ext4 |
| **Python** | ✅ | 3.13.12 (miniconda3 — system default) |
| **Node** | ✅ | v22.22.1 / npm 10.9.4 (via nvm) |
| **Disk** | ✅ | 1,007G total, 212G used (23%), **744G free** |
| **RAM** | ✅ | 23Gi total, 8.7Gi used, **14Gi available** |
| **Virtual Env** | ✅ | `.venv/` — 278 packages, `pip check` clean |
| **Linters** | ⚠️ | pylint, ruff, mypy **not installed** in venv |

---

## 2. Git State

| Metric | Value |
|--------|-------|
| **Branch** | `main` — ahead of `origin/main` by **4 commits** |
| **Commits** | 123 total on main |
| **Tags** | 33 tags (latest: `cycle-20260609-133100`) |
| **Remote** | `https://github.com/aaravjj2/Autopilot-public.git` — **PAT removed** ✅ |
| **Uncommitted** | 3 modified files: `data/kalshi_ticks.jsonl`, `data/training/corpus.jsonl`, `logs/cycle_final_report_v9.md` |
| **Untracked** | `logs/error_report_20260609_093122.txt`, `tests/data/` |
| **Submodules** | 9 external repos — **all initialized and checked out** |
| **Stashed** | Empty — nothing stashed |

### Git push blocked 🚫
PAT was removed from remote URL (security fix in commit `69f34ef`) but no credential helper was configured. `git push` will fail with `fatal: could not read Username for 'https://github.com': No such device or address`.

---

## 3. Running Services

| Service | PID | Port | Status | Uptime |
|---------|-----|------|--------|--------|
| **Backend API** (FastAPI) | 285356 | :8000 | ✅ HEALTHY — HTTP 200 (0.20s) | ~30h (since Jun 8) |
| **Frontend** (Next.js) | 294555 | :3000 | ✅ HEALTHY — HTTP 200 (0.07s) | ~30h (since Jun 8) |
| **Loop Daemon** (autopilot-continuous.py) | 257711 | — | ✅ RUNNING | ~22h (since Jun 8) |

**Note:** A third Python process (PID 590137) runs `api/app.py` on port 8000 — this is NOT serving (port is held by uvicorn 285356). Possibly a stale or duplicate process.

---

## 4. Source Code

| Metric | Count |
|--------|-------|
| **Python source files** | 168 in `src/apex/` |
| **Module packages** | 22 (agents, analytics, brain, cache, core, cross_asset, dashboard, defi, demo, domain, execution, fund, grpc, ingestion, integrations, layers, ml, monitor, monitoring, observability, repositories, risk, scheduler, security, services, streaming) |
| **Test files** | 78 in `tests/` |
| **Top-level scripts** | 7 (autopilot.py, backend_api.py, autopilot-continuous.py, migrate_consolidate_db.py, backup_db.py, build_apex_pdf.py, run_discord_bot.py) |
| **All Python files syntax-checked** | ✅ 168/168 parse clean |

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
| **Linters** | ❌ Missing | pylint, ruff, mypy — NOT installed in venv |

`pip check` — No broken requirements found.

---

## 6. Test Suite

| Metric | Value |
|--------|-------|
| **Tests collected** | **414** |
| **Passed** | **394** (100% pass rate) |
| **Failed** | **0** |
| **Skipped** | **20** (Playwright E2E — no browser runtime available) |
| **Duration** | **2m 25s** full suite |
| **Smoke tests** | **10/10 passed** in **4.90s** |

### Smoke Tests (10 critical-path)
- `test_arb_engine.py::test_topics_compatible_blocks_cross_topic_false_positives` ✅
- `test_auth_api.py::test_reads_are_public` ✅
- `test_brain_conviction.py::test_trend_score_bullish` ✅
- `test_dashboard_health.py::test_llm_route_ok_in_heuristic_mode` ✅
- `test_dashboard_health.py::test_llm_route_ok_when_groq_key_present` ✅
- `test_execution.py::test_execution_rejects_below_conviction_floor` ✅
- `test_finance_brain.py::test_knowledge_cards_have_unique_ids_and_content` ✅
- `test_quant_engine.py::test_fractional_kelly_produces_valid_sizes` ✅
- `test_risk_checks.py::test_r01_rejects_live_endpoint` ✅
- `test_scheduler_jobs.py::test_register_jobs_schedule_matches_callbacks` ✅

**Warnings:** 15 ChromaDB Pydantic deprecation warnings (upstream, non-blocking).

---

## 7. Data & ML Models

| Metric | Value |
|--------|-------|
| **Database total size** | ~60 MB |
| `data/audit.db` | **18 MB** — main audit database |
| `data/signal_quality.db` | 20 KB |
| `data/marketmind.db` | 0 bytes (empty?) |
| `data/discord_trades.db` | 12 KB |
| **Arb opportunities** | **357** (via API) |
| **Proposals** | **13** |
| **Positions** | **0** (paper mode) |
| **Active model** | `20260608T191239Z` — **92.17% accuracy** |
| **Candidate models** | **328** trained |
| **Training corpus** | **462 rows** in `data/training/corpus.jsonl` |
| **Kalshi ticks** | **3,662 records** |
| **Self-improvement loop** | Enabled |
| **Data freshness** | ⚠️ Last cache update ~37h ago (`is_stale: true`) |

---

## 8. Backend API Health

```json
{
    "status": "healthy",
    "timestamp": "2026-06-09T14:05:57Z",
    "last_cache_update": "2026-06-08T00:40:32Z",
    "is_stale": true,
    "alpaca_connected": true,
    "yfinance_ok": true,
    "opportunities": 357,
    "proposals": 13,
    "positions": 0,
    "ml": {
        "self_improvement_enabled": true,
        "active_model": { "version": "20260608T191239Z" }
    }
}
```

---

## 9. Known Issues (Active)

| # | Severity | Issue | Status |
|---|----------|-------|--------|
| 1 | 🔴 **High** | **Git push blocked** — PAT removed from remote URL, no credential helper configured. 4 commits + tags local only, not in remote. | Active — `69f34ef` fixed PAT exposure but broke push |
| 2 | 🟡 **Medium** | **Data stale** — Last cache update 37+ hours ago. Kalshi tick data and arb opportunities may be outdated. | Active |
| 3 | 🟡 **Medium** | **LLM routing all broken** — Groq 401, OpenCode Zen 429 → deterministic fallback only. No AI-powered analysis/planning. | Active — persistent across many cycles |
| 4 | 🟡 **Medium** | **Ollama not running** — TradingAgents health-check fails; L2 Agent Panel DEGRADED. | Active |
| 5 | 🟡 **Medium** | **Linters not installed** — pylint, ruff, mypy missing from venv. No automated code quality enforcement. | Active |
| 6 | 🟢 **Low** | **Duplicate backend process** — PID 590137 runs `api/app.py` but port 8000 is held by uvicorn 285356. Possibly a stale process. | Active |
| 7 | 🟢 **Low** | **marketmind.db empty** — 0 bytes, likely unused. | Active |
| 8 | 🟢 **Low** | **Chromadb Pydantic warnings** — 15 deprecation warnings from upstream. Non-blocking. | Active |

---

## 10. Issues Resolved Since Last Report

| Issue | Previous State | Current State |
|-------|---------------|---------------|
| **PAT in remote URL** | 🔴 Plaintext token `gho_6O...` exposed in origin URL | ✅ **REMOVED** — commit `69f34ef` stripped it |
| **.gitmodules missing** | 🔴 `fatal: no submodule mapping found` | ✅ **RESTORED** — 9 submodules listed and checked out |
| **Test suite** | 394/414 pass (v8) | ✅ **Stable** — 394/414 pass (v9), same reliable state |
| **Smoke tests** | 10/10 in 6.47s | ✅ **Improved** — 10/10 in **4.90s** |

---

## 11. Recommendations (Priority Order)

1. **🔴 Fix git push** — `gh auth login --with-token < ~/.ssh/gh_token` or configure `git credential.helper` to restore push capability
2. **🟡 Refresh data** — Trigger Kalshi poll cycle to update 37h-stale cache
3. **🟡 Revive LLM routing** — Fix Groq key or run ollama locally; stops deterministic fallback
4. **🟡 Install linters** — `pip install ruff mypy pylint` for automated code quality in CI
5. **🟢 Clean up** — Kill stale process 590137, investigate empty marketmind.db
6. **🟢 Daily push cadence** — Once push is fixed, establish regular commit+push schedule to back up 4 unsynced commits
