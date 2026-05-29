---
name: health-check
description: >
  Audit the environment, verify all required keys are set, check integration status,
  and validate the MarketMind-specific config (Kalshi, Polymarket, Anthropic).
slash_command: /health-check
---

# /health-check Workflow

Verify the full MarketMind + APEX environment is correctly configured.

---

## Step 1 — Required environment variables

Check that these are set in `.env` or `keys.env`:

```bash
python -c "
from apex.core.config import get_settings
s = get_settings()
checks = {
    'ANTHROPIC_API_KEY':        bool(s.anthropic_api_key),
    'ALPACA_API_KEY':           bool(s.alpaca_api_key),
    'ALPACA_PAPER_TRADE':       s.alpaca_paper_trade,
    'POLYMARKET_PAPER_ENABLED': s.polymarket_paper_trading_enabled,
    'KALSHI_ACCESS_KEY':        bool(s.kalshi_access_key),
    'ARB_MIN_NET_EDGE':         s.arb_min_net_edge,
    'KALSHI_MIN_VOLUME':        s.kalshi_min_volume_24h,
}
for k, v in checks.items():
    status = '✓' if v else '✗ MISSING'
    print(f'  {status}  {k} = {v}')
"
```

**Minimum required for MarketMind:**
- `ANTHROPIC_API_KEY` — for thesis streaming
- `ALPACA_API_KEY` + `ALPACA_PAPER_TRADE=True` — for paper execution
- `POLYMARKET_PAPER_TRADING_ENABLED=True`

**Optional but recommended:**
- `KALSHI_ACCESS_KEY` — for authenticated Kalshi endpoints
- `QUIVER_API_KEY` — for political tracker data

---

## Step 2 — Verify Kalshi public API is reachable

```bash
python -c "
import httpx
resp = httpx.get('https://external-api.kalshi.com/trade-api/v2/markets?status=open&limit=5', timeout=10)
data = resp.json()
print(f'Kalshi markets reachable: {len(data.get(\"markets\", []))} markets returned')
"
```

---

## Step 3 — Verify Polymarket Gamma API

```bash
python -c "
import httpx
resp = httpx.get('https://gamma-api.polymarket.com/markets?active=true&limit=5', timeout=10)
data = resp.json()
print(f'Polymarket Gamma reachable: {len(data)} markets returned')
"
```

---

## Step 4 — Verify Anthropic API

```bash
python -c "
import anthropic, os
client = anthropic.Anthropic()
resp = client.messages.create(
    model='claude-sonnet-4-20250514',
    max_tokens=20,
    messages=[{'role': 'user', 'content': 'Say OK'}],
)
print('Anthropic API:', resp.content[0].text)
"
```

---

## Step 5 — Verify SQLite schema

```bash
python -c "
from apex.main import build_engine
engine = build_engine()
tables = engine.store._conn.execute(
    \"SELECT name FROM sqlite_master WHERE type='table' ORDER BY name\"
).fetchall()
print('SQLite tables:', [t[0] for t in tables])
# Should include: arb_opportunities, audit_events, job_status, trades, etc.
"
```

---

## Step 6 — Run pre-deployment gates

```bash
python -c "
from apex.main import run_predeployment_gates
run_predeployment_gates()
"
```

Expected: `All pre-deployment gates passed.`

---

## Common Fixes

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError: apex` | Run `pip install -e ".[dev]"` from project root |
| `Settings` missing `kalshi_access_key` | Pull latest config or add field manually |
| Kalshi returns 403 | Auth not required for public endpoints; check you're not hitting a private endpoint |
| Polymarket returns empty list | Check `min_volume` parameter — try lowering to 1000 |
| SSE endpoint hangs | Verify `ANTHROPIC_API_KEY` is set; check `uvicorn` is running |
| ThesisCard shows blank | Add `"use client"` directive; EventSource needs browser context |
