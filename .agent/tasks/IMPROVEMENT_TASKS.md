# APEX Autopilot — Improvement Tasks

Generated 2026-05-28 from codebase analysis (23K LOC, 346 tests, 0 ruff errors, 89 mypy errors).

| # | Task | Impact | Effort | Status |
|---|------|--------|--------|--------|
| 1 | Fix 89 mypy errors across 41 source files | High — catches potential None-derefs and type mismatches | Large | ❌ |
| 2 | Resolve 18 pytest warnings (Pydantic V2 deprecations) | Medium — prevents breakage on Pydantic V3 | Medium | ❌ |
| 3 | Add ruff + mypy + coverage to CI pipeline | High — prevents regression | Medium | ❌ |
| 4 | Clean up 30+ stale root-level artifacts | Low — reduces repo confusion | Small | ❌ |
| 5 | Add Makefile with standardized dev workflow | Medium — consistent dev loop | Small | ✅ |
| 6 | Fix scheduler job duplication (live bug) | **High** — prevents overlapping execution | Small | ✅ |
| 7 | Resilient error handling for yfinance 404 + Ollama refusals | High — prevents cascading failures | Medium | ❌ |
| 8 | Cycle-resumption checkpoint in autopilot-continuous.py | Medium — saves work on restart | Medium | ❌ |
| 9 | Add code coverage measurement with pytest-cov | Medium — visibility into test gaps | Small | ❌ |
| 10 | Unify fragmented docs into structured docs/ tree | Low- Medium — reduces confusion | Medium | ❌ |

## Priority grouping

**Tier 1 — Live bugs affecting runtime stability:**
- #6 Scheduler job duplication
- #7 External API error handling

**Tier 2 — Quality gates preventing regression:**
- #1 mypy errors
- #3 CI pipeline
- #9 Coverage

**Tier 3 — Developer experience:**
- #2 Pydantic warnings
- #5 Makefile
- #8 Cycle checkpoint
- #4 Root clutter
- #10 Doc unification
