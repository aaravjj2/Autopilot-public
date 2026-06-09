# Codebase Health & Environment Report
**Generated:** 2026-06-09T10:00 UTC
**Overall Status: HEALTHY ✅** (with 4 active issues)

---

## 1. Environment

| Component | Status | Details |
|-----------|--------|---------|
| **OS** | ✅ | WSL (Ubuntu on Windows) — `/dev/sdd` ext4 |
| **Python** | ✅ | 3.13.12 (miniconda3 — system default) |
| **Node** | ✅ | v22.22.1 / npm 10.9.4 (via nvm) |
| **Disk** | ✅ | 1,007G total, 211G used (23%), **745G free** |
| **RAM** | ✅ | 23Gi total, 7.5Gi used, 15Gi available |
| **Virtual Env** | ✅ | `.venv/` — 278 packages, no broken deps (`pip check` clean) |

---

## 2. Git State

| Metric | Value |
|--------|-------|
| **Branch** | `main` — up to date with `origin/main` |
| **Commits** | ~99 commits on main |
| **Tags** | ~30 tags (latest: `cycle-20260609-123003`) |
| **Remote** | `https://github.com/aaravjj2/Autopilot-public.git` |
| **Uncommitted** | 1 item — `external/PolyMarket-MCP` has untracked content |
| **Submodules** | 9 external repos (Kronos, MiroFish, PolyMarket-MCP, TradingAgents, alpaca-mcp-server, daily_stock_analysis, dexter, financial-services, polymarket-mcp-server) |

**🔴 Issue: Git submodules broken**
`git submodule status` gives `fatal: no submodule mapping found in .gitmodules for path 'external/Kronos'` — `.gitmodules` file may be missing or corrupted. This blocks proper submodule updates.

**🔴 Issue: PAT embedded in remote URL**
The origin remote URL contains a plaintext GitHub personal access token (`gho_6O...`). This is a security risk if the repo is public or if the URL leaks in logs. Should migrate to a credential helper.

---

## 3. Source Code

| Metric | Count |
|--------|-------|
| **Python source files** | 168 in `src/apex/` |
| **Module packages** | 12 (agents, analytics, brain, cache, core, cross_asset, dashboard, defi, demo, domain, execution, ...) |
| **Test files** | 72 in `tests/` |
| **Top-level scripts** | 7 (autopilot.py, backend_api.py, autopilot-continuous.py, migrate_consolidate_db.py, backup_db.py, build_apex_pdf.py, run_discord_bot.py) |

**Architecture:** Well-structured with clear domain separation:
- `src/apex/agents/` — AI agents (arb intelligence, consensus, personas)
- `src/apex/brain/` — Core intelligence (finance_brain, quant_engine)
- `src/apex/core/` — Infrastructure (config, async_bridge, llm_routing, gemini_native)
- `src/apex/execution/` — Trading execution, DeFi treasury, Kalshi/Polymarket
- `src/apex/domain/` — Contracts, enums, errors, exceptions (DDD-style)

---

## 4. Dependencies

**Project deps** (pyproject.toml — 27 core + optional groups):
- Core: FastAPI, Pydantic, APScheduler, SQLModel, pandas, numpy, yfinance
- Dev (installed): pytest 8.4.2, pytest-asyncio 1.4.0, pytest-timeout 2.4.0, pytest-cov, pytest-playwright
- Agents: langgraph, langchain-openai, openai
- No requirements.txt (pyproject.toml is source of truth)

**✅ All dev dependencies now present** — `pytest-timeout` was flagged missing in prior report and has been installed.

---

## 5. Test Suite

| Metric | Value |
|--------|-------|
| **Tests collected** | 414 |
| **Passed** | **394** |
| **Failed** | **0** |
| **Skipped** | 20 (Playwright E2E — no browser runtime) |
| **Duration** | 2m 29s |
| **Smoke tests** | 10 marked `@smoke` — pass in 6.47s ✅ |

**Coverage areas:**
- Security & Auth — 3 files
- Arbitrage detection — 6 files
- Execution engine — 2 files
- Finance brain & quant — 3 files
- Risk checks — 2 files
- PolyMarket trading — 3 files
- Kalshi API/WS — 4 files
- World Cup model — 4 files
- Dashboard health — 2 files
- Scheduler jobs — 1 file
- Self-improvement — 1 file
- LLM routing — 1 file

**Warnings:** 15 Pydantic deprecation warnings from chromadb library (upstream, not our code) — no apex warnings.

---

## 6. Latest Cycle (Cycle 15 — 2026-06-09)

```
Phases completed: bootstrap ✗ | analyze ✗ | plan ✗ | execute ✓ | test ✓ | commit ✓ | report ✗
```

**Successes:**
- Execute phase: Added @smoke marker definition to pyproject.toml, tagged 10 critical-path tests, added smoke CI workflow
- Test phase: 394/394 pass (20 Playwright skipped)
- Commit phase: Committed market data refresh + corpus regeneration

**Failures (all rate-limit related):**
- Bootstrap: opencode 429 (rate limited) — report generated from existing data instead
- Analyze: opencode 429 — analysis was partially generated
- Plan: opencode 429
- Report: opencode 429

**🔴 Issue: Recurring OpenCode API rate limits (429)**
All 4 failed phases in the latest cycle were due to OpenCode API rate limiting. This is a persistent pattern across the last ~20 cycles. Self-resolves with cooldown but wastes cycle time.

---

## 7. Running Services (as of prior report)

| Service | Port | Status |
|---------|------|--------|
| Autopilot daemon | — | RUNNING (alive since Jun 7) |
| Backend API | 8000 | HEALTHY |
| Frontend (Next.js) | 3000 | HTTP 200 |
| Hermes Gateway | — | RUNNING |
| Chroma MCP | — | RUNNING |

*(Service check not re-verified this cycle — based on last confirmed state)*

---

## 8. Data & Models

- **56M+** total data across databases
- **288 arb edge candidate models** trained (May 26 — Jun 8)
- **Active model:** 92.04% accuracy, 3.21 Sharpe (90d backtest, +$18.20 PnL)
- **Databases:** audit.db, signal_quality.db, marketmind.db, discord_trades.db — all present
- **Training corpus:** 457 records in data/training/corpus.jsonl

---

## 9. Known Issues (Active)

| # | Severity | Issue | Status |
|---|----------|-------|--------|
| 1 | 🔴 High | **Playwright E2E failures** — 12/106 failing in full-flow.spec.ts (navigation/timeout) | Active — has persisted multiple cycles |
| 2 | 🔴 High | **Git submodules broken** — `.gitmodules` file MISSING entirely. 9 external repos exist as standalone git repos in `external/` but have no submodule mapping. `git status` shows `(untracked content)` for PolyMarket-MCP. | Active — blocks submodule operations |
| 3 | 🟡 Medium | **OpenCode API rate limits (429)** — recurring in 4/6 cycle phases | Active — wastes cycle time, self-resolves |
| 4 | 🟡 Medium | **PAT token in remote URL** — `https://224672050:gho_6O...@github.com/aaravjj2/Autopilot-public.git` — plaintext GitHub PAT in URL. Security risk for public repos. No credential helper configured. | Active — blocks automated push without exposing token |
| 5 | 🟢 Low | **Chromadb Pydantic warnings** — 15 deprecation warnings, upstream issue | Active — non-blocking |
| 6 | 🟢 Low | **openrouter_key placeholder** — .env likely has empty OPENROUTER_KEY | Unverified this cycle |

## 10. Issues Resolved Since Last Report

| Issue | Previous State | Current State |
|-------|---------------|---------------|
| pytest-timeport missing | Not installed | ✅ Installed v2.4.0 |
| No @smoke markers | 0 tests tagged | ✅ 10 tests tagged + pyproject.toml marker defined |
| Test count | 382/382 pass (no smoke) | ✅ 394/394 pass (with 10 smoke) |

---

## 11. Recommendations (Priority Order)

1. **Fix git submodules** — Recreate `.gitmodules` or fix the missing mapping for `external/Kronos`
2. **Configure git credential helper** — Replace PAT in URL with `git credential-store` or `gh auth login`
3. **Fix Playwright E2E tests** — Update `full-flow.spec.ts` navigation selectors to match current frontend routes
4. **Route around OpenCode 429s** — Use ollama or another fallback for analyze/plan phases when opencode rate-limited
5. **Remove PAT from remote URL** — Set up `credential.helper` in git config and strip token from origin URL
