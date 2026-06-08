# Codebase Health & Environment Report
**Generated:** 2026-06-08T18:13 UTC
**Overall Status: HEALTHY**

---

## Environment
- **OS:** WSL (Windows Subsystem for Linux)
- **Python:** 3.13.12 (miniconda3) | **Node:** v22.22.1 | **NPM:** 10.9.4
- **Total Packages:** 277 installed in `.venv/`
- **Disk:** 749Gi free of 1007Gi | **RAM:** 13Gi free of 23Gi

## Git
- **Branch:** main | **98 commits** | **22 tags** (latest: cycle-20260608-090916)
- **Remote:** https://github.com/aaravjj2/Autopilot-public.git (HTTPS, no credential helper)
- **Uncommitted:** 10 files (modified .py, .jsonl, .json, .toml + untracked candidate models)
- **Submodules:** 9 external repos (Kronos, MiroFish, PolyMarket-MCP, TradingAgents, alpaca-mcp-server, daily_stock_analysis, dexter, financial-services, polymarket-mcp-server)

## Running Services
| Service | Port | Status |
|---------|------|--------|
| Autopilot daemon | — | RUNNING (alive since Jun 7) |
| Backend API | 8000 | HEALTHY |
| Frontend (Next.js) | 3000 | HTTP 200 |
| Hermes Gateway | — | RUNNING |
| Chroma MCP | — | RUNNING |

## Backend Health
- **Alpaca:** connected | **YFinance:** ok | **Kalshi WS:** connected
- **Arb opportunities:** 339 | **Proposals:** 13 | **Positions:** 0 (paper)
- **ML Self-Improvement:** enabled
- **Active Model:** 20260608T140041Z — **92.04% accuracy** | **3.21 Sharpe** (90d backtest, +$18.20 PnL)
- **Training corpus:** 452 rows, 115 labeled, 16 resolved arb opportunities

## Test Suite (411 total)
| Batch | Result |
|-------|--------|
| All non-slow tests (382) | **382/382 PASS** — zero failures |
| Slow tests (9) | deselected (not run) |
| Playwright E2E (1 file) | skipped |
| **Warnings** | 3x PydanticDeprecatedSince20 (SQLModel, non-blocking) |

## Data & Models
- **56M** total data | **2.3M** models directory
- **288 arb edge candidate models** trained from May 26 — Jun 8
- **Active candidate:** 20260608T140041Z (trained today)
- **Databases:** audit.db, signal_quality.db, marketmind.db, discord_trades.db — all present

## Error Analysis (62 total error logs)
All 62 recent errors follow the **same pattern**: `HTTP 429 Rate limit exceeded` on `opencode` API calls (test, commit, and report phases). No code failures, no import errors, no test regressions. Rate limits self-resolve with cooldown; no action needed.

## Issues Found
1. **pytest-timeout not installed** — listed in pyproject.toml [dev] deps but missing
2. **No @smoke markers** — PR CI marker defined but zero tests use it
3. **untracked candidate_* dirs** — 4 model directories not in .gitignore
4. **openrouter_key placeholder** — still "FILL_IN_YOUR_OPENROUTER_KEY_HERE"
5. **Git push blocked** — HTTPS remote without credential helper (manual entry needed)
6. **3x SQLModel deprecation warnings** — Pydantic V2 migration needed eventually

## Recommendations (Priority Order)
1. Install pytest-timeout, add @smoke markers, fix .gitignore
2. Configure git credential helper for automated push
3. Set real OpenRouter key or remove from config
4. Audit SQLModel warnings when time permits
