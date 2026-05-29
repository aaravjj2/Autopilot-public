# APEX Autopilot Engine — Documentation Index

**Status:** ✓ PRODUCTION-READY (Paper Trading Mode)  
**Last Verified:** May 28, 2026  
**Environment:** WSL (Python 3.13.12, 394 packages)

---

## Documentation Files

### 📊 HEALTH_REPORT.md (10.2 KB)
**Comprehensive health assessment** of the entire codebase.

Contents:
- Executive summary
- Environment status (Python, packages, git)
- Architecture layers (L0-L4) detailed breakdown
- Core services inventory
- Data layer & persistence
- Frontend/Backend status
- Configuration overview
- Test suite details
- Code quality metrics
- Known issues & workarounds
- Roadmap status

**Use when:** Auditing architecture, understanding system state, troubleshooting

---

### 🚀 QUICK_START.txt (2.9 KB)
**Action-oriented checklist** for rapid onboarding.

Sections:
- Status summary
- Verification steps
- Optional environment setup
- API startup commands
- Common development tasks
- Database information
- Configuration reference
- Known limitations
- Paper trading guarantee
- Next steps

**Use when:** Setting up development environment, quick reference, onboarding

---

### 📋 ENVIRONMENT_STATUS.txt (12.5 KB)
**Current system snapshot** with configuration details.

Contents:
- System environment details
- Package ecosystem (394 packages)
- Architecture layers status
- Core services checklist
- Data layer inventory
- Frontend/Backend configuration
- Configuration files status
- Test suite summary
- Code quality standards
- Import verification results
- Known issues with fixes
- Performance baselines
- Security & compliance status
- Roadmap progress
- Next steps guide

**Use when:** Debugging environment, verifying configuration, onboarding

---

## Quick Reference

### File Locations

**Project Root:**
```
/home/aarav/Aarav/Autopilot/
├── HEALTH_REPORT.md           (← You are here)
├── QUICK_START.txt
├── ENVIRONMENT_STATUS.txt
├── AGENTS.md                  (Project architecture)
├── pyproject.toml
└── Makefile
```

**Source Code:**
```
src/apex/
├── layers/                    L0-L4 pipeline
│   ├── l0/ingestion.py
│   ├── l1/brain.py
│   ├── l2/agent_panel.py
│   ├── l3/execution.py
│   ├── l3/risk_checks.py
│   └── l4/observability.py
├── services/                  Core services
│   ├── arb_engine.py
│   ├── backtest_engine.py
│   ├── settlement_auditor.py
│   ├── pm_trading.py
│   └── engine.py
├── core/                      Configuration & utilities
│   ├── config.py
│   ├── logging.py
│   └── retry.py
├── domain/                    Data models
│   └── models.py
└── repositories/              Data access
    └── sqlite_store.py
```

**Frontend/Backend:**
```
autopilot-local/
├── backend/                   FastAPI server
│   └── main.py
└── frontend/                  Next.js dashboard
    ├── package.json
    └── app/page.tsx
```

**Testing:**
```
tests/
├── test_arb_engine.py
├── test_agent_panel.py
├── test_backtest_engine.py
└── ... (73 test files, 346 tests)
```

**Configuration:**
```
.env                           Primary configuration (144 lines)
.env.example                   Reference copy
.agent/rules/                  Development conventions
├── apex-conventions.md
├── paper-only.md
└── streaming.md
```

**Data:**
```
data/
├── audit.db                   Primary database (SQLite)
├── marketmind.db              Market data cache
├── discord_trades.db          Trade notifications
├── chromadb/                  Embeddings store
└── backups/                   Automatic backups (5 sets)
```

---

## Quick Commands

### Verification
```bash
# Check Python environment
python --version                    # Expected: 3.13.12
pip list | grep -E "(pytest|pydantic|fastapi)"

# Test critical imports
python -c "from apex.core.config import get_settings; print(get_settings().llm_provider)"

# Verify test suite
pytest --collect-only -q
```

### Testing
```bash
make test              # Standard test run
make test-full         # With coverage
make coverage          # Coverage report
pytest tests/test_arb_engine.py -v
```

### Code Quality
```bash
make lint              # Check style
make lint-fix          # Auto-fix
make typecheck         # Type safety
make format            # Format code
```

### Development Servers
```bash
# Terminal 1: Backend API
python -m uvicorn autopilot-local.backend.main:app --reload
# → http://localhost:8000
# → http://localhost:8000/docs (API docs)

# Terminal 2: Frontend UI
cd autopilot-local/frontend && npm run dev
# → http://localhost:3000
```

### Database Operations
```bash
# Inspect database
sqlite3 data/audit.db
  > .schema
  > SELECT COUNT(*) FROM audit_logs;
  > .quit

# Backup current state
cp data/audit.db data/backups/manual_$(date +%s).db

# View backups
ls -lt data/backups/
```

---

## Architecture Overview

### L0 Ingestion (10.2 KB)
Market data collection from Polymarket, Kalshi, Alpaca, Tradier. Normalization and preprocessing.

### L1 Finance Brain (18.0 KB)
Contract scoring, basis point calculation, multi-leg arb analysis.

### L2 Agent Panel (23.0 KB)
Multi-agent decision framework with consensus mechanism and reasoning transparency.

### L3 Execution (15.6 KB)
Order routing, dual-leg submission, state machine for order lifecycle.

### L3 Risk Checks (27.4 KB)
14-point risk gate including:
- **M01_PAPER_REQUIRED** (paper-only enforcement — FIRST CHECK)
- Position limits, volatility checks, counterparty validation

### L4 Observability (2.0 KB)
Audit logging, telemetry, SSE streaming to frontend.

---

## Key Statistics

| Metric | Value |
|--------|-------|
| Total Python Files | 133+ |
| Test Files | 73 |
| Total Tests | 346 |
| Lines of Code | ~50,000+ |
| Database Backups | 5 timestamped sets |
| Makefile Targets | 25 |
| API Endpoints | FastAPI auto-docs |
| Frontend Pages | Next.js framework |
| Packages Installed | 394 |
| Python Version | 3.13.12 |
| Git Commits | 600+ (recent) |

---

## Development Standards (APEX Conventions)

✓ **Language:** Python 3.11+  
✓ **Type Hints:** Full annotations with `from __future__ import annotations`  
✓ **Configuration:** Pydantic `BaseSettings` via `get_settings()`  
✓ **Logging:** `get_logger(__name__)` from `apex.core.logging`  
✓ **Retries:** `call_with_retries()` for external APIs  
✓ **Database:** `SQLiteStore` exclusively  
✓ **Paper Trading:** `M01_PAPER_REQUIRED` first in every path  
✓ **Domain Models:** `@dataclass` contracts  
✓ **Testing:** pytest with 346+ tests  

---

## Known Issues (Non-Blocking)

| Issue | Impact | Fix |
|-------|--------|-----|
| No `requirements.txt` | Low | Use `pyproject.toml` (standard) |
| `.env.local` missing | Low | Copy `.env` if local overrides needed |
| `backend/.env` not present | Low | Symlink or copy root `.env` |
| yfinance 404 (SMH, SOXX, etc.) | Low | Arb scoring adapts to missing data |
| Ollama 11434 fails if not running | Low | Graceful fallback to Groq |

---

## Roadmap (Week 4/10)

- ✓ **Weeks 1-3:** High-frequency ingestion, L2 agent hive
- ✓ **Week 4:** ML-driven predictive arbitrage (production testing)
- → **Weeks 5-7:** DeFi treasury, VaR limits, autonomous execution
- ○ **Weeks 8-10:** Multi-agent orchestration, dashboards

---

## Support & Reference

### Documentation
- `AGENTS.md` — Project architecture overview
- `.agent/rules/apex-conventions.md` — Code standards
- `.agent/rules/paper-only.md` — Trading enforcement
- `.agent/rules/streaming.md` — Observability patterns

### Configuration
- `.env` — Primary configuration (144 lines)
- `pyproject.toml` — Project metadata and dependencies
- `pytest.ini` — Test runner configuration

### Code Examples

**Import Settings (Correct):**
```python
from apex.core.config import get_settings
settings = get_settings()  # ✓ Cached singleton
```

**Logging:**
```python
from apex.core.logging import get_logger
logger = get_logger(__name__)
logger.info("message")
```

**Database Access:**
```python
from apex.repositories.sqlite_store import SQLiteStore
store = SQLiteStore()
audit_logs = store.fetch_audit_logs()
```

**External APIs (with retry):**
```python
from apex.core.retry import call_with_retries
result = call_with_retries(
    lambda: requests.get(url),
    max_attempts=3
)
```

**Type-Hinted Domain Model:**
```python
from __future__ import annotations
from dataclasses import dataclass

@dataclass
class BacktestResult:
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
```

---

## Next Steps

1. **Verify Environment**
   ```bash
   make test-full
   ```

2. **Start Development Stack**
   ```bash
   # Terminal 1
   python -m uvicorn autopilot-local.backend.main:app --reload
   
   # Terminal 2
   cd autopilot-local/frontend && npm run dev
   
   # Terminal 3 (free for commands)
   ```

3. **Open Interfaces**
   - Backend Docs: http://localhost:8000/docs
   - Frontend UI: http://localhost:3000

4. **Follow APEX Conventions**
   - Read `.agent/rules/apex-conventions.md`
   - Use `get_settings()`, `get_logger()`, `call_with_retries()`
   - Enforce paper trading (`M01_PAPER_REQUIRED`)
   - Use `SQLiteStore` exclusively

---

## Status Summary

✓ **Environment:** Production-ready  
✓ **Architecture:** Fully implemented (L0-L4)  
✓ **Testing:** 346 tests across 73 files  
✓ **Frontend/Backend:** Ready to start  
✓ **Database:** Operational with backups  
✓ **Paper Trading:** Enforced  
✓ **Configuration:** Complete  
✓ **Documentation:** Comprehensive  

**READY FOR DEVELOPMENT** 🚀

---

Generated: May 28, 2026 | Mode: Comprehensive Health Check | Duration: ~8 seconds
