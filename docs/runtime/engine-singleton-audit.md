# Engine Singleton Audit

Date: 2026-05-27  
Scope: `backend_api.py`, `src/apex/main.py`, `src/apex/services/engine.py`

## Objective

Verify backend request paths do not repeatedly instantiate the core engine and that singleton lifecycle behavior is explicit.

## Findings

1. `backend_api.py` exposes `get_cached_engine()` as the primary accessor.
2. `get_cached_engine()` initializes `_engine_singleton` once using `build_engine()` and reuses it thereafter.
3. Request handlers use cached state and service functions; no hot-path endpoint calls `build_engine()` directly.
4. Lifespan startup performs cache refresh and loop task creation without recreating engine objects per request.

## Verification commands

```bash
cd /home/aarav/Aarav/Autopilot
rg "def get_cached_engine|build_engine\(" backend_api.py src/apex/main.py src/apex/services/engine.py
PYTHONPATH=src:. pytest tests/test_dashboard_snapshot.py -q
```

## Risk notes

- If future handlers call `build_engine()` directly, response latency and memory churn may spike.
- Keep engine creation behind `get_cached_engine()` or a dependency-injected singleton.
