---
name: risk-stack
description: >
  Use this skill when adding or modifying arb-specific risk checks (M01–M06) to
  APEX's execution layer. Covers the full paper-arb risk path, instrument type additions
  (KALSHI_EVENT, ARB_PAIR), and the atomic dual-leg paper order submission pattern.
  Trigger when implementing run_arb_paper(), adding M05/M06 gates, or debugging rejected arb trades.
compatibility: Antigravity CLI (agy), Claude Code, Gemini CLI
---

# Arb Risk Stack Skill

## New Instruments (add to domain/enums.py)

```python
class Instrument(str, Enum):
    EQUITY   = "EQUITY"
    CALL     = "CALL"
    PUT      = "PUT"
    VERTICAL = "VERTICAL"
    STRADDLE = "STRADDLE"
    IRON_CONDOR = "IRON_CONDOR"
    POLYMARKET_EVENT = "POLYMARKET_EVENT"
    # ── MarketMind additions ──
    KALSHI_EVENT = "KALSHI_EVENT"
    ARB_PAIR     = "ARB_PAIR"        # both legs together
```

---

## Full M01–M06 Arb Risk Check Sequence

```python
# src/apex/layers/l3/risk_checks.py — add after existing checks

from apex.domain.models import ArbOpportunity

class ArbRiskCheckResult:
    def __init__(self):
        self.passed: list[str] = []
        self.failed: list[str] = []
        self.rejection_reason: str | None = None

    @property
    def all_passed(self) -> bool:
        return not self.failed


def run_arb_paper(opp: ArbOpportunity, settings: "Settings") -> ArbRiskCheckResult:
    """
    Run the full M01–M06 arb risk stack.
    Returns ArbRiskCheckResult. If any check fails, stops early.
    All checks are paper-only — no real money path exists.
    """
    result = ArbRiskCheckResult()

    # M01 — Paper-only mode enforced
    def m01_paper_only() -> tuple[bool, str]:
        if not settings.alpaca_paper_trade:
            return False, "M01_PAPER_REQUIRED: ALPACA_PAPER_TRADE must be True for arb"
        if not settings.polymarket_paper_trading_enabled:
            return False, "M01_PAPER_REQUIRED: POLYMARKET_PAPER_TRADING_ENABLED must be True for arb"
        return True, ""

    # M02 — Net edge above floor
    def m02_min_edge() -> tuple[bool, str]:
        if opp.net_edge < settings.arb_min_net_edge:
            return False, f"M02_EDGE_BELOW_FLOOR: {opp.net_edge:.4f} < {settings.arb_min_net_edge}"
        return True, ""

    # M03 — Both platforms have sufficient volume
    def m03_volume_check() -> tuple[bool, str]:
        min_vol = settings.kalshi_min_volume_24h
        if opp.volume_kalshi < min_vol:
            return False, f"M03_KALSHI_LOW_VOLUME: {opp.volume_kalshi:,.0f} < {min_vol:,.0f}"
        if opp.volume_poly < min_vol:
            return False, f"M03_POLY_LOW_VOLUME: {opp.volume_poly:,.0f} < {min_vol:,.0f}"
        return True, ""

    # M04 — Ask prices are within valid range (0.01 – 0.99)
    def m04_price_sanity() -> tuple[bool, str]:
        if not (0.01 <= opp.kalshi_yes_ask <= 0.99):
            return False, f"M04_KALSHI_PRICE_INVALID: {opp.kalshi_yes_ask}"
        if not (0.01 <= opp.poly_no_ask <= 0.99):
            return False, f"M04_POLY_PRICE_INVALID: {opp.poly_no_ask}"
        return True, ""

    # M05 — Settlement auditor must not BLOCK
    def m05_settlement_pass() -> tuple[bool, str]:
        if opp.settlement_match_score < 0.45:
            return False, (
                f"M05_SETTLEMENT_BLOCKED: score={opp.settlement_match_score:.2f} "
                f"flags={opp.settlement_flags}"
            )
        return True, ""

    # M06 — Daily arb P&L loss limit (don't over-expose to arb positions)
    def m06_daily_arb_limit() -> tuple[bool, str]:
        # Placeholder: real implementation reads today's arb P&L from SQLite
        # and blocks if daily loss exceeds 1% of paper bankroll
        return True, ""

    checks = [
        ("M01", m01_paper_only),
        ("M02", m02_min_edge),
        ("M03", m03_volume_check),
        ("M04", m04_price_sanity),
        ("M05", m05_settlement_pass),
        ("M06", m06_daily_arb_limit),
    ]

    for name, check_fn in checks:
        passed, reason = check_fn()
        if passed:
            result.passed.append(name)
        else:
            result.failed.append(name)
            result.rejection_reason = reason
            break  # fail-fast

    return result
```

---

## Atomic Dual-Leg Paper Order Submission

```python
# src/apex/layers/l3/execution.py — add method to ExecutionService

from apex.domain.models import ArbOpportunity, ArbRiskCheckResult

async def submit_arb_paper_orders(
    self,
    opp: ArbOpportunity,
    stake_usd: float = 50.0,
) -> tuple[str | None, str | None]:
    """
    Submit both arb legs atomically. If either leg fails, cancel the other.
    Returns (kalshi_order_id, poly_order_id) or (None, None) on failure.
    """
    risk = run_arb_paper(opp, self.settings)
    if not risk.all_passed:
        LOGGER.warning(
            "Arb risk check FAILED for %s: %s", opp.id, risk.rejection_reason
        )
        self.store.append_event(AuditEvent(
            event_type=EventType.RISK_REJECTION,
            rejection_reason=risk.rejection_reason,
            raw_payload={"arb_id": opp.id, "checks": risk.failed},
        ))
        return None, None

    # Paper-simulate Kalshi leg (no real Kalshi paper API — use internal simulator)
    kalshi_order_id = f"KALSHI_PAPER_{opp.id[:8]}"
    LOGGER.info("Kalshi paper leg submitted: %s (%.3f YES)", kalshi_order_id, opp.kalshi_yes_ask)

    # Submit Poly NO leg via paper broker
    try:
        poly_order_id = await self.broker.submit_polymarket_paper(
            market_id=opp.poly_market_id,
            outcome="NO",
            stake_usd=stake_usd,
            price=opp.poly_no_ask,
        )
    except Exception as e:
        LOGGER.error("Poly paper leg failed for %s: %s — aborting arb", opp.id, e)
        # Kalshi leg was only paper-simulated, nothing to cancel
        return None, None

    # Write both legs to SQLite
    self.store.upsert_arb_opportunity(opp)
    LOGGER.info("Arb paper order complete: %s | %s", kalshi_order_id, poly_order_id)
    return kalshi_order_id, poly_order_id
```

---

## AuditEvent Types for Arb

Add to `src/apex/domain/enums.py`:

```python
class EventType(str, Enum):
    # existing...
    ARB_DETECTED    = "ARB_DETECTED"
    ARB_RISK_PASSED = "ARB_RISK_PASSED"
    ARB_RISK_FAILED = "ARB_RISK_FAILED"
    ARB_PAPER_SUBMITTED = "ARB_PAPER_SUBMITTED"
    ARB_RESOLVED    = "ARB_RESOLVED"
```

---

## Key Safety Invariants

1. **R01 must always pass** — `ALPACA_PAPER_TRADE=True` is non-negotiable
2. **No real Kalshi trading** — all Kalshi orders are simulation-only (no real Kalshi trade API)
3. **M05 BLOCK = hard stop** — settlement score < 0.45 always blocks, even if edge is high
4. **Atomic or nothing** — if Poly leg fails, do NOT record a Kalshi-only position
