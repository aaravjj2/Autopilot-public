# APEX Code Conventions Rule

Always apply these conventions when writing or editing any code in this repository.

---

## Python Style

- Python 3.11+ with full type annotations on all function signatures
- `from __future__ import annotations` at top of every module
- `@dataclass` for all domain objects — no raw dicts passed between layers
- `Pydantic BaseSettings` only in `core/config.py` — never inline config classes
- Use `|` for union types (`str | None`), never `Optional[str]`
- Max line length: 100 characters

## Imports

```python
# Correct order:
from __future__ import annotations          # 1. future
import stdlib_module                        # 2. stdlib
import third_party                          # 3. third party
from apex.core.logging import get_logger    # 4. local absolute imports
```

Never use wildcard imports (`from x import *`).

## Logging

- Always: `LOGGER = get_logger(__name__)` at module top
- Never: `print()`, `logging.basicConfig()`, or `logging.getLogger()`
- Log levels: DEBUG for per-symbol detail, INFO for job milestones, WARNING for degraded paths, ERROR for failures

## Error Handling

- Catch specific exceptions, not bare `except:`
- Use `except Exception as exc:` when you must catch broadly — always log `exc`
- Never swallow exceptions silently in production paths
- Use `apex.core.retry.call_with_retries()` for all external API calls

## File Organization

- One class or group of related functions per file
- New integrations → `src/apex/integrations/`
- New services (orchestration) → `src/apex/services/`
- New domain models → `src/apex/domain/models.py`
- New enums → `src/apex/domain/enums.py`
- Tests → `tests/test_<module_name>.py`

## No Direct Database Access

Never access SQLite directly from a layer (L0–L4). All DB operations go through `SQLiteStore`.

## Environment Variables

Every new config value must be:
1. Added to `src/apex/core/config.py` with a `Field(alias=...)` and default
2. Documented in `.env.example` with a comment explaining the value
