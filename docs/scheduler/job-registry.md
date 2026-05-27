# Scheduler Job Registry

Date: 2026-05-27  
Primary file: `src/apex/scheduler/jobs.py`

## Purpose

Track scheduled jobs, ownership, cadence, and idempotency expectations so operators can diagnose missing executions quickly.

## Runtime modes

- **In-process loops** (default via `backend_api.py` lifespan):
  - `arb_scan_loop`
  - `pm_agents_loop`
  - `equity_autopilot_loop`
  - optional `self_improvement_loop`
- **Separate scheduler daemon** (optional): expected only when `APEX_EXPECT_SCHEDULER_DAEMON=true`.

## Registry snapshot

| Job | Trigger | Source | Idempotency expectation |
|---|---|---|---|
| Arb scan | interval | `backend_api.py::arb_scan_loop` | Safe re-run; overwrites opportunity snapshot |
| PM agents | interval | `backend_api.py::pm_agents_loop` | Safe re-run; no duplicate fills in paper mode |
| Equity autopilot | interval | `backend_api.py::equity_autopilot_loop` | Proposal generation only; no duplicate fills |
| Self improvement | interval (opt-in) | `backend_api.py::self_improvement_loop` | Model promotion guarded by status checks |

## Health checks

```bash
cd /home/aarav/Aarav/Autopilot
curl -s http://127.0.0.1:8000/health | python -m json.tool
./status.sh
```

## Sign-off criteria

1. `/health` returns a `scheduler` block with mode + loop flags.
2. If daemon is expected, `/health.scheduler.separate_process_running` is `true`.
3. No unresolved exceptions in backend logs for active loops.
