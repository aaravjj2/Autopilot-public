---
name: daily-cycle
description: >
  Debug or re-run the full APEX daily cycle including arb scanning. Useful when
  the scheduler fails, a job is stuck, or you want to force a full refresh.
slash_command: /daily-cycle
---

# /daily-cycle Workflow

Debug and re-run the APEX daily cycle with MarketMind extensions.

---

## Step 1 — Health check

**Agent:** QA Agent

Run the integration health check:

```bash
python -c "
from apex.main import build_engine
engine = build_engine()
engine.system_health_check()
print('Health OK')
"
```

Expected output: `Health OK`. If it fails, note which integration is missing.

---

## Step 2 — Run arb scan manually

```bash
python -c "
from apex.main import build_engine
from apex.services.arb_engine import ArbEngine

engine = build_engine()
arb = ArbEngine(settings=engine.settings, store=engine.store)
opps = arb.scan()
print(f'Found {len(opps)} arb opportunities')
for o in opps[:3]:
    print(f'  {o.kalshi_ticker}: net_edge={o.net_edge:.3f}, settlement={o.settlement_match_score:.2f}')
"
```

---

## Step 3 — Run full daily cycle

```bash
apex-engine
```

Or for a single cycle:
```bash
python -m apex.main
```

Watch the logs for:
- `[arb_scan] Found N opportunities`
- `[ArbEngine] net_edge=X for TICKER`
- `[M05] SETTLEMENT_BLOCKED` (if any are filtered)
- `[PAPER_SUBMITTED]` for approved trades

---

## Step 4 — Check scheduler state

```bash
python -c "
from apex.main import build_engine
engine = build_engine()
print(engine.store.get_job_status_today())
"
```

If a job shows `failed`, check the audit log:
```bash
python -c "
from apex.main import build_engine
engine = build_engine()
events = engine.store.get_recent_events(limit=20)
for e in events:
    print(e.event_type, e.rejection_reason or '', str(e.raw_payload)[:100])
"
```

---

## Step 5 — Force re-run a specific job

```bash
python -c "
from apex.main import build_engine
from apex.scheduler.jobs import arb_scan
engine = build_engine()
arb_scan(engine)
"
```
