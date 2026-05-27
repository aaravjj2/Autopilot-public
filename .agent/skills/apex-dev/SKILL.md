---
name: apex-dev
description: >
  Use this skill for any development task touching the APEX Autopilot Engine codebase
  (src/apex/). Covers layer architecture, Settings/Pydantic config, dataclass contracts,
  integration wiring, logging patterns, and scheduler job authoring. Trigger when asked to
  add a new integration, modify the build_engine() factory, extend domain models, or write
  a new scheduler job.
compatibility: Antigravity CLI (agy), Claude Code, Gemini CLI, Cursor
---

# APEX Engine Development Skill

## Architecture Overview

The APEX engine is a 5-layer paper-trading autonomous execution system:

```
L0  DataIngestionService      ← market data, options, PM signals, news adapters
L1  FinanceBrainService        ← opportunity scoring (0–10 conviction)
L2  MultiAgentPanelService     ← specialist agents → bull/bear debate → judge
L3  ExecutionService           ← risk checks (R01–R15) → broker submission
L4  ObservabilityService       ← append-only audit log, P&L, feedback memory
```

All layers are wired in `src/apex/main.py:build_engine()` which returns `ApexEngine`.

---

## Config Pattern (Pydantic Settings)

All config lives in `src/apex/core/config.py` as `Settings(BaseSettings)`.

```python
# Add new env var:
new_feature_enabled: bool = Field(default=False, alias="NEW_FEATURE_ENABLED")
new_api_key: str = Field(default="", alias="NEW_API_KEY")
```

Access anywhere via:
```python
from apex.core.config import get_settings
settings = get_settings()
if settings.new_feature_enabled:
    ...
```

**Never** instantiate `Settings()` directly outside `get_settings()` — it's lru_cached.

---

## Logging Pattern

```python
from apex.core.logging import get_logger
LOGGER = get_logger(__name__)

LOGGER.info("Starting %s for symbol %s", job_name, symbol)
LOGGER.warning("Skipping %s — missing data", symbol)
LOGGER.error("Failed to fetch: %s", exc)
```

Never use `print()`. Never use `logging.getLogger()` directly.

---

## Domain Model Pattern

New models go in `src/apex/domain/models.py` as `@dataclass`:

```python
@dataclass
class ArbOpportunity:
    id: str
    kalshi_ticker: str
    poly_market_id: str
    question: str
    kalshi_yes_ask: float       # reconstructed from bid
    poly_no_ask: float          # from Gamma REST bestAsk
    gross_spread: float         # 1.00 - kalshi_yes_ask - poly_no_ask
    net_edge: float             # gross_spread minus fee adjustment
    settlement_match_score: float  # 0.0–1.0 from SettlementAuditor
    detection_ts: datetime
    resolution_ts: datetime | None = None
    outcome: str | None = None  # "WIN" | "LOSS" | "PUSH"
    pnl: float | None = None
```

New enums go in `src/apex/domain/enums.py`:
```python
class Instrument(str, Enum):
    # existing...
    KALSHI_EVENT = "KALSHI_EVENT"
    ARB_PAIR = "ARB_PAIR"
```

---

## Adding a New Integration Adapter

1. Create `src/apex/integrations/my_adapter.py`
2. Define a typed client class with `__init__(self, settings: Settings)`
3. Add an `Optional[MyAdapter]` field to `IntegrationHub` in `src/apex/integrations/hub.py`
4. Wire it in `build_engine()` in `src/apex/main.py`:
   ```python
   my_adapter = MyAdapter(settings) if settings.my_api_key else None
   ```
5. Add the env var to `Settings` in `core/config.py`
6. Add to `IntegrationRegistry.validate()` in `src/apex/integrations/repo_registry.py`

---

## Adding a Scheduler Job

Jobs are defined in `SCHEDULE` list in `src/apex/scheduler/jobs.py`:

```python
SCHEDULE: list[tuple[str, int, int, int | None]] = [
    # (job_name, hour, minute, day_of_week)  day_of_week None = every market day
    ("arb_scan", 9, 25, None),      # 5 min before market open
    ("arb_scan_intraday", 11, 0, None),
    ("arb_scan_intraday", 13, 0, None),
]
```

Then add the handler in the same file:

```python
def arb_scan(engine: ApexEngine) -> None:
    from apex.services.arb_engine import ArbEngine
    arb_engine = ArbEngine(settings=engine.settings, store=engine.store)
    opportunities = arb_engine.scan()
    engine.store.upsert_arb_opportunities(opportunities)
    engine.observability.emit_arb_event(opportunities)
```

Wrap with `idempotent_job()` — it prevents double-execution on the same run date.

---

## SQLite Store Patterns

All DB operations go through `src/apex/repositories/sqlite_store.py`.

```python
# Adding a new table — add migration in __init__:
def _migrate(self) -> None:
    self._conn.execute("""
        CREATE TABLE IF NOT EXISTS arb_opportunities (
            id TEXT PRIMARY KEY,
            kalshi_ticker TEXT,
            poly_market_id TEXT,
            question TEXT,
            kalshi_yes_ask REAL,
            poly_no_ask REAL,
            gross_spread REAL,
            net_edge REAL,
            settlement_match_score REAL,
            detection_ts TEXT,
            resolution_ts TEXT,
            outcome TEXT,
            pnl REAL
        )
    """)

# Upsert pattern:
def upsert_arb_opportunity(self, opp: ArbOpportunity) -> None:
    self._conn.execute(
        "INSERT OR REPLACE INTO arb_opportunities VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (opp.id, opp.kalshi_ticker, opp.poly_market_id, ...)
    )
    self._conn.commit()
```

---

## Retry Utility

```python
from apex.core.retry import call_with_retries

result = call_with_retries(
    lambda: my_api_call(),
    max_attempts=engine.settings.ingestion_fetch_max_attempts,
    backoff_sec=engine.settings.ingestion_fetch_backoff_sec,
    label="kalshi_market_fetch",
)
```

---

## Test Patterns

```python
# tests/test_arb_engine.py
import pytest
from unittest.mock import MagicMock, patch
from apex.services.arb_engine import ArbEngine
from apex.core.config import Settings

def test_arb_engine_detects_spread():
    settings = Settings()
    store = MagicMock()
    engine = ArbEngine(settings=settings, store=store)

    with patch.object(engine, "_fetch_kalshi_markets", return_value=[...]):
        with patch.object(engine, "_fetch_poly_markets", return_value=[...]):
            opps = engine.scan()
            assert len(opps) > 0
            assert opps[0].net_edge >= 0.02
```
