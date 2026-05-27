# Improvement Plan

## Completed (Committed)

- **Multi-agent panel** with market analyst, fundamentals analyst, options specialist, PM analyst, bull/bear advocates, judge, and Dexter adversarial review
- **Consolidated SQLite DB** (`data/audit.db`) with WAL mode, foreign keys, and unified schema
- **P&L tracking** (`pl_attribution()`) with Discord trade separation
- **Strict trade separation**: engine skips Discord-tracked symbols; Discord bot uses isolated keys
- **Dashboard upgrades**: Equity Curve, P&L Attribution, Discord Trades, Signal Quality tabs
- **CI/CD pipeline** with 81 passing tests
- **P1.1**: Options buying power check before spread submission (`broker.py:255`)
- **P1.3**: Daily loss limit enforced intraday via `loss_cut_scan` (`loss_cut_brain.py:53-81`)
- **P1.6**: `_move_pct` sentinel guard for div/zero (`exit_monitor.py:25-26`)
- **P2.1**: Trailing stop-loss via `trailing_stop_pct` setting (`config.py:188`, `loss_cut_brain.py:128-166`)
- **P2.2**: Cross-position correlation risk check (`engine.py:578`, `risk_checks.py:194`)
- **P4.3**: Graceful shutdown via SIGTERM handler (`service.py:100-131`)
- **P4.4**: Daily SQLite backup at 5:50 AM to `data/backups/` with 30-day retention (`engine.py:1164-1194`)
- **P5.1**: Legacy root-level `exit_manager.py` removed
- **P5.3**: Cross-field `model_validator` on Settings (`config.py:241-265`)
- **P5.4**: All `datetime.utcnow()` calls replaced with `datetime.now(timezone.utc)` across codebase
- **P5.5**: OCC symbol generation standardised via `apex.domain.option_symbols`

## Priority 1 — Fix Known Issues

### 1.1 Alpaca option margin check before spread submission ✅
_Done — `_submit_alpaca_options_order` checks `options_buying_power` vs `_options_risk_budget()`._

### 1.2 Option symbol fallback when chain data has wrong expiry ✅
_Done — `_try_validate_occ_for_any_expiry()` in `broker.py` scans ±14 days for a valid expiry when the preferred one has no matching OCC symbols._

### 1.3 Daily loss limit not enforced intraday ✅
_Done — `_daily_loss_exceeded()` in `loss_cut_brain.py` queries today's completed trades and closes all positions when limit is breached._

### 1.4 Polymarket paper positions not included in loss cut scan ✅
_Done — `loss_cut_scan` now handles `PM:` positions via `_pm_position_pnl_pct()` with a flat 4% threshold. `SQLiteStore.get_pm_positions()` provides the data._

### 1.5 Proposal `take_profit` never triggers for option spreads ✅
_Done — `engine.py:498-506` uses Alpaca `current_price` for option positions instead of yfinance underlying price._

### 1.6 `_move_pct` in exit_monitor may divide by zero ✅
_Done — returns sentinel `-999.0` when entry <= 0; caller returns `invalid_entry_price` exit._

### 1.7 `fast_fill_peek()` — reusable fill confirmation function ✅
_Done — Extracted from inline code in `execution.py` into a standalone `fast_fill_peek()` function._

## Priority 2 — Feature Gaps

### 2.1 Trailing stop-loss ✅
_Done — `trailing_stop_pct` in settings; `loss_cut_scan` tracks peak P&L via `_peak_pnl()`._

### 2.2 Cross-position correlation risk ✅
_Done — `_compute_correlations() → _r08_correlation()` blocks proposals when `corr > 0.75`._

### 2.3 Real Polymarket MCP integration ✅
_Available in `external/polymarket-mcp-server/`; wired via `hub.py:123`._

### 2.4 Multi-timeframe exit checks (5min + 15min VWAP) ✅

### 2.5 Position-level P&L dashboard ✅
_Done — `GET /api/positions` endpoint added to `autopilot-local/backend/main.py` returns per-position P&L, entry/current price, hold time, stop/take levels._

### 2.6 Options real-time quote feed ✅
_Done — `AlpacaStreamClient` in `alpaca_adapter.py` with `subscribe_option_quotes()` using Alpaca WebSocket SIP stream._

### 2.7 Order fill confirmation reliability ✅
_Done — `fast_fill_peek()` in `execution.py` tries `AlpacaStreamClient.wait_for_fill()` WebSocket path before REST polling fallback._

## Priority 3 — Testing & Quality

### 3.1 Integration test for full order lifecycle ✅
_Done — `test_full_order_lifecycle` covers propose → submit → fill → track position → exit via stop-loss and take-profit, with audit event assertions._

### 3.2 Loss cut brain integration test ✅

### 3.3 Option chain validation test ✅

### 3.4 Scheduler resilience test ✅
_Done — `test_catch_up_morning_pipeline_skips_before_931` and `test_catch_up_morning_pipeline_runs_after_931` verify catch-up behaviour with mocked time._

### 3.5 sqlite_store concurrent access test ✅
_Done — `test_concurrent_read_write_wal` runs 4 writer + 4 reader threads concurrently against WAL-mode SQLite, verifies no corruption._

## Priority 4 — Infrastructure & Operations

### 4.1 Health endpoint enrichment ✅
_Done — `GET /healthz?deep=1` returns probes, Alpaca equity/BP/positions/unrealized P&L, today's trade count & P&L._

### 4.2 Systemd / container deployment ✅
_Done — `deploy/apex-scheduler.service`, `deploy/apex-discord-bot.service`, `deploy/apex-dashboard.service` with restart policy and journald logging._

### 4.3 Graceful shutdown ✅
_Done — SIGTERM/SIGINT handlers registered in `scheduler/service.py`._

### 4.4 Database backup automation ✅
_Done — daily 5:50 AM cron job via `database_backup()` with 30-day retention._

### 4.5 Environment file audit / `.gitignore` hardening ✅
_Done — `.gitignore` blocks all `.env`/`keys.env` variants; `.pre-commit-config.yaml` with `detect-private-key` hook._

## Priority 5 — Code Quality & Architecture

### 5.1 Remove legacy `exit_manager.py` ✅
_Done — root-level file removed._

### 5.2 Consolidate Discord exit monitoring ✅
_Done — `engine.monitor_discord_exits` delegates to `DiscordExitManager.check_once()`; duplicate logic removed from engine._

### 5.3 Settings type validation ✅
_Done — `model_validator` on `Settings` with 4 cross-field rules._

### 5.4 Replace `datetime.utcnow()` deprecation warnings ✅
_Done — zero remaining `utcnow()` calls across all source files._

### 5.5 Standardize OCC symbol generation ✅
_Done — `format_occ_option_symbol()` in `option_symbols.py` is canonical; `discord_bot.py` delegates to it._

## Summary

| Priority | Category | Items |
|----------|----------|-------|
| P1 | Fix Known Issues | 7 bugs — **7/7 done** |
| P2 | Feature Gaps | 7 features — **6/7 done** (2.5 position dashboard pending) |
| P3 | Testing & Quality | 5 test gaps — **4/5 done** (P3.1 full lifecycle pending*) |
| P4 | Infrastructure | 5 ops items — **5/5 done** |
| P5 | Code Quality | 5 cleanup items — **5/5 done** |

**28 items total** — **27 done**, 1 remaining. **85 tests passing** (up from 61).
