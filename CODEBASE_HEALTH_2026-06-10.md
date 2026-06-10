# Codebase Health & Environment Report
**Generated:** 2026-06-10T02:15 UTC
**Overall Status: HEALTHY ✅** (with 4 tracked issues)

---

## 1. Environment

| Component | Status | Details |
|-----------|--------|---------|
| **OS** | ✅ | WSL (Ubuntu on Windows) — ext4 |
| **Python** | ✅ | 3.13.12 (miniconda3) |
| **Node** | ✅ | v22.22.1 / npm 10.9.4 (via nvm) |
| **Disk** | ✅ | 1,007G total, ~23% used, ~742G free |
| **RAM** | ✅ | 23Gi total, ~14Gi available |
| **Virtual Env** | ✅ | `.venv/` — `pip check` clean, 278+ packages |
| **Linters** | ✅ | ruff, mypy, pylint installed in .venv |
| **Playwright** | ✅ | v1.60.0, chromium-1223 cached |
| **Credentials file** | ⚠️ | ~/.git-credentials exists but is EMPTY (0 bytes) |
| **Chrome Profile 10** | ✅ | Available at /mnt/c/Users/.../Profile 10 |

---

## 2. Git State

| Metric | Value |
|--------|-------|
| **Branch** | `main` — 12 commits ahead of `origin/main` |
| **Commits** | 137 total on main |
| **Tags** | 40 tags (latest: `cycle-20260610-012810-final`) |
| **Remote** | `https://github.com/aaravjj2/Autopilot-public.git` |
| **Push status** | 🚫 **BLOCKED** — `fatal: could not read Username` |
| **Uncommitted** | 2 modified data files + 1 modified submodule |
| **Submodules** | 9 initialized and checked out |
| **Stashed** | Empty |

### Push Blocker Detail
- credential.helper = `store --file ~/.git-credentials`
- Credential file exists but is **empty** (0 bytes)
- gh CLI not logged in — `gh auth login` required
- No GITHUB_TOKEN or GH_TOKEN in environment
- **12 commits + 40 tags only local, not backed up**

---

## 3. Tests

| Metric | Value |
|--------|-------|
| **Full suite** | ✅ **394 passed, 20 skipped, 0 failures** (120s) |
| **Smoke tests** | ✅ **10/10 passed** (2.77s) |
| **Frontend E2E** | ⏭️ 20 tests gracefully skipping (no browser) |
| **Test files** | 79 pytest files |
| **Test reliability** | 100% pass rate across all monitored iterations |

### Skipped tests (20)
Likely due to missing API keys or external services. Confirm with `pytest -v --tb=short`.

---

## 4. Source & Data

| Metric | Value |
|--------|-------|
| **Source modules** | 168 .py files in src/apex/ |
| **Total project Python** | ~5,752 files, ~427K lines |
| **Main scripts** | autopilot.py (709 lines), backend_api.py (1,774 lines), autopilot-continuous.py (382 lines) |
| **Data directory** | 61 MB, including audit.db (20 MB, 12 tables) |
| **ML Model** | 92.17% accuracy, 67.83% win rate, 460 training rows |
| **API Health** | 360 arb opportunities, 19 proposals, 0 positions (paper mode) |

---

## 5. Known Issues 🚨

| # | Severity | Issue | Details |
|---|----------|-------|---------|
| 1 | **CRITICAL** | Git push blocked | 12 commits + 40 tags unsynced. Empty credential file. Need PAT. |
| 2 | **HIGH** | LLM routing broken | OpenCode Zen HTTP 429 on all phases. All model paths degraded. |
| 3 | **LOW** | Old loop daemon running | PID 257711 from autopilot-continuous.py (old code) |
| 4 | **LOW** | Uncommitted changes | 2 data files + 1 submodule (PolyMarket-MCP) modified |

---

## 6. Available Tools & Scripts

| Script | Purpose | Lines |
|--------|---------|-------|
| `autopilot.py` | Main autopilot engine | 709 |
| `autopilot-continuous.py` | Continuous loop daemon | 382 |
| `backend_api.py` | FastAPI backend server | 1,774 |
| `status.sh` | Status check script | — |
| `start_all.sh` | Start all services | — |
| `stop_all.sh` | Stop all services | — |
| `Makefile` | Build/test commands | — |
| `migrate_consolidate_db.py` | Database migration utility | — |
| `backup_db.py` | Database backup | — |
