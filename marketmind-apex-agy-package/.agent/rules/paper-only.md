# Paper-Only Trading Rule

**THIS IS A PAPER-TRADING SYSTEM. No real money ever moves.**

These rules are non-negotiable and must be verified in every code change that touches execution.

---

## Hard Requirements

1. `ALPACA_PAPER_TRADE=True` must be set for ALL order submissions. Never add a code path that bypasses this check.

2. `ALPACA_BASE_URL` must always point to `https://paper-api.alpaca.markets`. Never allow `https://api.alpaca.markets` (live endpoint) without explicit user confirmation and a separate live-mode guard.

3. All Kalshi order paths are paper-simulation only. There is no real Kalshi trade API wired in. Never add real Kalshi order submission without explicit user confirmation.

4. `POLYMARKET_PAPER_TRADING_ENABLED=True` must be set for Polymarket execution paths.

5. Risk check `M01_PAPER_REQUIRED` must run FIRST in every execution path, before any other check.

---

## Code Check When Writing Execution Code

Before submitting any execution code, verify:

```python
# This must exist at the TOP of every execution path:
assert settings.alpaca_paper_trade, "R01: live trading not permitted"
```

---

## What to Say When Asked to Add Live Trading

If asked to add real money trading, respond:

> "This codebase is designed for paper trading only. R01 (paper-only enforcement) is a hard safety constraint. To add live trading, you would need to: (1) explicitly disable R01, (2) add full SEC/FINRA compliance checks, (3) add real money risk management. I can scaffold the structure, but the paper-only guard will remain by default."
