from __future__ import annotations

from datetime import datetime, timedelta, timezone

from apex.core.logging import get_logger
from apex.domain.models import ArbOpportunity, AuditEvent
from apex.domain.enums import EventType
from apex.repositories.sqlite_store import SQLiteStore

LOGGER = get_logger(__name__)

_NOW = datetime.now(timezone.utc)


def _opp(
    *,
    oid: str,
    ticker: str,
    poly_id: str,
    question: str,
    k_ask: float,
    p_no: float,
    net: float,
    match: float,
    flags: list[str],
    vol_k: float = 45_000.0,
    vol_p: float = 38_000.0,
) -> ArbOpportunity:
    gross = round(1.0 - k_ask - p_no, 4)
    return ArbOpportunity(
        id=oid,
        kalshi_ticker=ticker,
        poly_market_id=poly_id,
        question=question,
        kalshi_title=question,
        poly_title=question,
        kalshi_yes_ask=k_ask,
        poly_no_ask=p_no,
        gross_spread=gross,
        net_edge=net,
        settlement_match_score=match,
        settlement_flags=flags,
        volume_kalshi=vol_k,
        volume_poly=vol_p,
        category="macro",
        kelly_fraction=min(round(net * 10.0, 3), 0.5),
        detection_ts=_NOW - timedelta(minutes=2),
    )


DEMO_ARBITRAGE_OPPORTUNITIES: list[ArbOpportunity] = [
    _opp(
        oid="demo-fed-jun",
        ticker="KXFEDDEC-26JUN",
        poly_id="0xdemo-fed-jun",
        question="Fed cuts rates in June 2026?",
        k_ask=0.41,
        p_no=0.52,
        net=0.058,
        match=0.88,
        flags=[],
    ),
    _opp(
        oid="demo-btc-100k",
        ticker="KXBTC-100K-DEC26",
        poly_id="0xdemo-btc-100k",
        question="Bitcoin above $100k on Dec 31 2026?",
        k_ask=0.38,
        p_no=0.55,
        net=0.044,
        match=0.81,
        flags=["resolution_wording_diff"],
    ),
    _opp(
        oid="demo-spx-6k",
        ticker="KXINX-6000-26",
        poly_id="0xdemo-spx-6k",
        question="S&P 500 closes above 6000 in 2026?",
        k_ask=0.44,
        p_no=0.49,
        net=0.031,
        match=0.76,
        flags=[],
    ),
    _opp(
        oid="demo-eth-etf",
        ticker="KXETH-ETF-FLOWS",
        poly_id="0xdemo-eth-etf",
        question="ETH spot ETF weekly inflows exceed $500M?",
        k_ask=0.29,
        p_no=0.64,
        net=0.027,
        match=0.72,
        flags=["liquidity_asymmetric"],
    ),
    _opp(
        oid="demo-election-turnout",
        ticker="KXVOTE-2026-MID",
        poly_id="0xdemo-vote-mid",
        question="2026 US midterm turnout above 50%?",
        k_ask=0.51,
        p_no=0.42,
        net=0.062,
        match=0.91,
        flags=[],
    ),
    _opp(
        oid="demo-oil-80",
        ticker="KXOIL-WTI-80",
        poly_id="0xdemo-oil-80",
        question="WTI crude above $80 by Q3 2026?",
        k_ask=0.33,
        p_no=0.60,
        net=0.019,
        match=0.68,
        flags=["settlement_source_diff"],
    ),
    _opp(
        oid="demo-reject-demo",
        ticker="KXDEMO-RISK-FAIL",
        poly_id="0xdemo-risk-fail",
        question="Demo: risk gate rejection scenario",
        k_ask=0.92,
        p_no=0.05,
        net=0.001,
        match=0.35,
        flags=["BLOCK", "low_liquidity"],
        vol_k=500.0,
        vol_p=400.0,
    ),
]

DEMO_AUDIT_EVENTS: list[AuditEvent] = [
    AuditEvent(
        event_type=EventType.SYSTEM_ALERT,
        symbol="APEX",
        agent="system",
        raw_payload={"message": "DEMO_MODE active — paper trading only (R01)", "demo_mode": True},
    ),
    AuditEvent(
        event_type=EventType.GATE_RESULT,
        symbol="KXFEDDEC-26JUN",
        risk_check="R01",
        raw_payload={"gate": "R01", "passed": True, "message": "Paper account verified"},
    ),
    AuditEvent(
        event_type=EventType.ARB_RISK_FAILED,
        symbol="KXDEMO-RISK-FAIL",
        risk_check="M07",
        rejection_reason="Insufficient liquidity on Kalshi book",
        raw_payload={"gate": "M07", "passed": False},
    ),
    AuditEvent(
        event_type=EventType.ARB_PAPER_SUBMITTED,
        symbol="KXFEDDEC-26JUN",
        conviction=7.2,
        order_id="demo-kalshi-001",
        raw_payload={
            "kalshi_order_id": "demo-kalshi-001",
            "poly_order_id": "demo-poly-001",
            "stake_usd": 50.0,
        },
    ),
    AuditEvent(
        event_type=EventType.PROPOSAL_CREATED,
        symbol="SPY",
        agent="L2_panel",
        conviction=6.8,
        raw_payload={
            "specialists": ["market", "fundamentals", "options", "pm"],
            "judge": "approve",
            "demo_mode": True,
        },
    ),
]


def _demo_already_seeded(store: SQLiteStore) -> bool:
    """True when demo audit rows exist (safe for DEMO_MODE restarts)."""
    rows = store.read_table("audit_log", limit=50)
    for row in rows:
        payload = row.get("raw_payload") or {}
        if isinstance(payload, str):
            try:
                import json

                payload = json.loads(payload)
            except Exception:
                payload = {}
        if isinstance(payload, dict) and payload.get("demo_mode"):
            return True
        if row.get("symbol") == "KXFEDDEC-26JUN" and row.get("event_type") == "ARB_PAPER_SUBMITTED":
            return True
    opps = store.list_arb_opportunities(limit=5)
    return any(o.get("id") == "demo-fed-jun" for o in opps)


def seed_demo_database(store: SQLiteStore) -> dict[str, int]:
    """Populate SQLite with demo arb rows and audit events (idempotent)."""
    from apex.core.config import get_settings

    settings = get_settings()
    if settings.showcase_mode or settings.demo_mode:
        return seed_showcase_database(store)

    if _demo_already_seeded(store):
        LOGGER.info("Demo seed skipped: database already contains demo rows")
        return {"opportunities": len(DEMO_ARBITRAGE_OPPORTUNITIES) + 6, "audit_events": len(DEMO_AUDIT_EVENTS)}

    store.save_arb_opportunities(DEMO_ARBITRAGE_OPPORTUNITIES)

    resolved = _opp(
        oid="demo-resolved-win",
        ticker="KXDEMO-RESOLVED",
        poly_id="0xdemo-resolved",
        question="Demo resolved arb (won)",
        k_ask=0.45,
        p_no=0.48,
        net=0.04,
        match=0.85,
        flags=[],
    )
    resolved.outcome = "WIN"
    resolved.pnl = 12.40
    resolved.resolution_ts = _NOW - timedelta(days=3)

    resolved_loss = _opp(
        oid="demo-resolved-loss",
        ticker="KXDEMO-LOSS",
        poly_id="0xdemo-loss",
        question="Demo resolved arb (lost)",
        k_ask=0.52,
        p_no=0.41,
        net=-0.02,
        match=0.70,
        flags=["resolution_wording_diff"],
    )
    resolved_loss.outcome = "LOSS"
    resolved_loss.pnl = -8.20
    resolved_loss.resolution_ts = _NOW - timedelta(days=5)

    extra_resolved = []
    for i, (oid, win) in enumerate(
        [
            ("demo-resolved-2", True),
            ("demo-resolved-3", True),
            ("demo-resolved-4", False),
            ("demo-resolved-5", False),
        ]
    ):
        o = _opp(
            oid=oid,
            ticker=f"KXDEMO-{i}",
            poly_id=f"0xdemo-{oid}",
            question=f"Demo training label {i}",
            k_ask=0.40 + i * 0.02,
            p_no=0.50,
            net=0.03 if win else -0.01,
            match=0.80,
            flags=[],
        )
        o.outcome = "WIN" if win else "LOSS"
        o.pnl = 6.0 if win else -4.0
        o.resolution_ts = _NOW - timedelta(days=7 + i)
        extra_resolved.append(o)

    store.save_arb_opportunities([resolved, resolved_loss, *extra_resolved])

    n_audit = 0
    for ev in DEMO_AUDIT_EVENTS:
        store.append_event(ev)
        n_audit += 1

    n_opps = len(DEMO_ARBITRAGE_OPPORTUNITIES) + 6
    LOGGER.info(
        "Demo seed complete: %d opportunities, %d audit events",
        n_opps,
        n_audit,
    )
    return {
        "opportunities": n_opps,
        "audit_events": n_audit,
    }


def seed_showcase_database(store: SQLiteStore) -> dict[str, int]:
    """Large hackathon-style dataset: N arbs + M proposal audit events."""
    from apex.core.config import get_settings
    from apex.demo.bulk_seed import generate_bulk_arb_opportunities, generate_demo_proposal_events

    settings = get_settings()
    n_arb = int(settings.showcase_arb_count)
    n_prop = int(settings.showcase_proposal_count)

    existing = store.list_arb_opportunities(limit=5)
    if any(str(o.get("id", "")).startswith("demo-arb-") for o in existing):
        LOGGER.info("Showcase seed skipped: bulk demo rows already present")
        return {"opportunities": n_arb, "audit_events": n_prop + len(DEMO_AUDIT_EVENTS)}

    arbs = generate_bulk_arb_opportunities(n_arb)
    store.save_arb_opportunities(arbs)

    n_audit = 0
    for ev in DEMO_AUDIT_EVENTS:
        store.append_event(ev)
        n_audit += 1
    for ev in generate_demo_proposal_events(n_prop):
        store.append_event(ev)
        n_audit += 1

    LOGGER.info(
        "Showcase seed complete: %d arb opportunities, %d audit/proposal events",
        len(arbs),
        n_audit,
    )
    return {"opportunities": len(arbs), "audit_events": n_audit}


def demo_opportunities_list() -> list[ArbOpportunity]:
    """Fresh copy with rotated detection_ts for stream animation."""
    from apex.core.config import get_settings

    settings = get_settings()
    if settings.showcase_mode or settings.demo_mode:
        from apex.demo.bulk_seed import generate_bulk_arb_opportunities

        return generate_bulk_arb_opportunities(int(settings.showcase_arb_count))

    out: list[ArbOpportunity] = []
    for i, base in enumerate(DEMO_ARBITRAGE_OPPORTUNITIES):
        o = ArbOpportunity(
            id=base.id,
            kalshi_ticker=base.kalshi_ticker,
            poly_market_id=base.poly_market_id,
            question=base.question,
            kalshi_title=base.kalshi_title,
            poly_title=base.poly_title,
            kalshi_yes_ask=base.kalshi_yes_ask,
            poly_no_ask=base.poly_no_ask,
            gross_spread=base.gross_spread,
            net_edge=base.net_edge,
            settlement_match_score=base.settlement_match_score,
            settlement_flags=list(base.settlement_flags),
            volume_kalshi=base.volume_kalshi,
            volume_poly=base.volume_poly,
            category=base.category,
            kelly_fraction=base.kelly_fraction,
            detection_ts=_NOW - timedelta(seconds=15 * i),
        )
        out.append(o)
    return sorted(out, key=lambda x: -x.net_edge)
