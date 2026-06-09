# Improvement Tasks — Generated 2026-06-09 15:05 UTC

Derived from comprehensive codebase analysis: 660+ iterations, 131 commits,
414 tests, 358 arb opportunities, 328 candidate ML models.

---

## P0 🔴 Critical

### T1. Fix git push (credential helper / gh auth)
**Why:** 12 commits + 33 tags are local-only. PAT was removed in `69f34ef` (security fix) but
no credential helper configured. One disk failure loses everything.
**Location:** `git remote -v` → origin at https://github.com/aaravjj2/Autopilot-public.git
**Evidence:** `fatal: could not read Username for 'https://github.com': No such device or address`
**Fix:** Configure gh CLI with token, or set `git credential.helper`, or switch to SSH.

### T2. Refresh stale data (Kalshi cache + arb scan trigger)
**Why:** Last cache update ~38h ago (`is_stale: true`). Kalshi WS stale (2417s since last frame).
358 arb opportunities may be outdated. Self-improvement loop disabled in scheduler.
**Location:** Backend API health endpoint, scheduler config, `jobs.py`
**Fix:** Trigger arb_scan_loop manually, or restart scheduler with all loops enabled.

### T3. Fix autopilot-continuous.py missing config crash
**Why:** `cfg = json.loads((STATE / "config.json").read_text())` at lines 22-24 has zero error
handling. If `.state/config.json` is missing or corrupted → `FileNotFoundError` kills the daemon
before any logging is set up. Fresh clone can't start.
**Location:** `autopilot-continuous.py:22` and `autopilot.py:24`
**Evidence:** Identified in error logs from cycle 636 analysis.
**Fix:** Wrap in try/except FileNotFoundError with helpful error + graceful exit.

---

## P1 🟡 High

### T4. Fix Playwright E2E trading navigation failure
**Why:** `full-flow.spec.ts` line 15 — clicking "Trading" sidebar link doesn't navigate to
`/dashboard/trading/`. The test expects URL transition but sidebar click doesn't register
or routing doesn't fire.
**Location:** `autopilot-local/frontend/tests/e2e/full-flow.spec.ts:15`
**Evidence:** Error logs confirm `expect(page).toHaveURL(/trading/)` failed — got `/dashboard` instead.
**Fix:** Investigate sidebar navigation handler — hydration issue or route guard blocking nav.

### T5. Convert bare `except Exception:` handlers to specific types
**Why:** 30+ instances of `except Exception:` in `src/apex/` silently swallow errors. Makes
debugging nearly impossible when something fails silently.
**Location:** Across 14+ files: `market_facade.py`, `tradingagents_adapter.py`, `market_data.py`,
`broker.py`, `polymarket_adapter.py`, `kalshi_ws.py`, `brightdata_mcp_client.py`,
`brightdata_intelligence.py`, `thesis_service.py`, `health_server.py`, `kalshi_adapter.py`,
`news_regime_adapters.py`, `scheduler/service.py`, `core/llm_routing.py`
**Evidence:** search_files confirmed 30+ instances; ACTION_CHECKLIST.md recommends fixing.
**Fix:** Replace each with specific exception types or at minimum log the error.

### T6. Enable self-improvement loop + fix scheduler job duplication
**Why:** `self_improvement_loop` is disabled in scheduler. Also "Adding job tentatively" logged
every iteration — indicates job duplication or accumulation issue.
**Location:** `scheduler/service.py`, `jobs.py`, engine config
**Evidence:** API health endpoint shows `"self_improvement_loop": false`
**Fix:** Enable the loop and fix APScheduler job deduplication.

---

## P2 🟢 Medium

### T7. Eliminate remaining print() statements (~50 locations)
**Why:** `wc2026_autopilot/autopilot.py`, `build_apex_pdf.py`, `seed_db.py`, `backtest.py` use
raw `print()` instead of logging. Breaks observability — no timestamps, no levels, can't filter.
**Location:** Multiple files in `wc2026_autopilot/`, `build_apex_pdf.py`, and scripts.
**Evidence:** grep search found 30+ print() statements; ACTION_CHECKLIST.md notes ~50 total.
**Fix:** Convert to logger.info()/warning()/error() calls.

### T8. Kill stale duplicate backend process (PID 590137)
**Why:** Root-owned process running `.venv/bin/python api/app.py --host 0.0.0.0 --port 8000`
from Apex-Terminal project. Port 8000 is already held by uvicorn 285356. Wastes resources.
**Location:** PID 590137 (root-owned)
**Evidence:** `ps aux` shows it running, health report confirms duplication.
**Fix:** `sudo kill 590137`

### T9. Fix deprecation warnings (Chromadb Pydantic + Starlette)
**Why:** 15 ChromaDB `model_fields` deprecation warnings + 1 StarletteDeprecationWarning per
test run. Clutters test output, masks real issues.
**Location:** pyproject.toml filterwarnings, test output (currently 18 warnings suppressed)
**Evidence:** pytest output shows warnings from Starlette testclient + ChromaDB Pydantic V2.11.
**Fix:** Pin compatible ChromaDB version or update filterwarnings. Migrate from Starlette testclient.

### T10. Restart loop daemon to pick up utcnow() fix
**Why:** PID 257711 still uses old code with `utcnow()` deprecation. The source fix was committed
but the running daemon never restarted. Fix is invisible until restart.
**Location:** PID 257711 (autopilot-continuous.py)
**Evidence:** Health report notes daemon not restarted since before the fix commit.
**Fix:** Kill and restart the daemon process.

---

## Scoring & Tracking

| # | Task | Severity | Effort | Impact | Dependencies |
|---|------|----------|--------|--------|-------------|
| 1 | Fix git push | 🔴 Critical | 30m | Prevents all remote backup | GitHub token |
| 2 | Refresh stale data | 🟡 High | 15m | Restores live market data | Backend running |
| 3 | Fix config crash | 🔴 Critical | 15m | Prevents daemon death | — |
| 4 | Fix E2E nav failure | 🟡 High | 45m | Restores frontend test suite | Frontend running |
| 5 | Convert bare excepts | 🟡 High | 2-3h | Enables proper error debugging | — |
| 6 | Enable self-improvement loop | 🟡 High | 30m | Restores ML auto-training | Scheduler |
| 7 | Remove print statements | 🟢 Medium | 2h | Better observability | — |
| 8 | Kill stale process | 🟢 Medium | 5m | Frees port resources | sudo access |
| 9 | Fix deprecation warnings | 🟢 Medium | 30m | Clean test output | — |
| 10 | Restart loop daemon | 🟢 Medium | 5m | Picks up source fixes | — |
