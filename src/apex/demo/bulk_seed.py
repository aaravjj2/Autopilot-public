"""Generate large demo datasets for hackathon / showcase deployments."""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

from apex.domain.models import ArbOpportunity, AuditEvent
from apex.domain.enums import EventType

_NOW = datetime.now(timezone.utc)

_CATEGORIES = ("macro", "politics", "crypto", "sports", "finance", "fed", "rates")
_QUESTION_TEMPLATES = (
    "Will {topic} exceed {threshold} by {year}?",
    "Will {topic} fall below {threshold} before {year}?",
    "Fed {topic} in {year}?",
    "{topic} above {threshold} on Dec 31 {year}?",
    "Will {topic} win {year} election cycle?",
)
_TOPICS = (
    "Bitcoin",
    "Ethereum",
    "S&P 500",
    "Nasdaq",
    "10Y yield",
    "unemployment",
    "CPI",
    "GDP growth",
    "oil WTI",
    "gold",
    "Tesla",
    "Apple",
    "Fed funds rate",
    "recession",
    "inflation",
)


def _stable_id(prefix: str, index: int) -> str:
    digest = hashlib.sha256(f"{prefix}:{index}".encode()).hexdigest()[:12]
    return f"demo-{prefix}-{index:03d}-{digest}"


def generate_bulk_arb_opportunities(count: int = 100) -> list[ArbOpportunity]:
    """Deterministic synthetic cross-market arb rows for UI / ML showcase."""
    out: list[ArbOpportunity] = []
    for i in range(count):
        topic = _TOPICS[i % len(_TOPICS)]
        template = _QUESTION_TEMPLATES[i % len(_QUESTION_TEMPLATES)]
        year = 2026 + (i % 3)
        threshold = 50 + (i % 40)
        question = template.format(topic=topic, threshold=threshold, year=year)
        k_ask = round(0.28 + (i % 47) * 0.01, 2)
        p_no = round(0.35 + (i % 38) * 0.01, 2)
        gross = round(1.0 - k_ask - p_no, 4)
        net = round(gross - 0.07 * (1.0 - k_ask), 4)
        if net <= 0:
            net = round(0.008 + (i % 5) * 0.004, 4)
        match = round(0.72 + (i % 25) * 0.01, 2)
        flags: list[str] = []
        if i % 11 == 0:
            flags.append("resolution_wording_diff")
        if i % 17 == 0:
            flags.append("low_volume")
        oid = _stable_id("arb", i)
        out.append(
            ArbOpportunity(
                id=oid,
                kalshi_ticker=f"KXDEMO-{i:04d}",
                poly_market_id=f"0xdemo-poly-{i:04d}",
                question=question,
                kalshi_title=question,
                poly_title=question,
                kalshi_yes_ask=k_ask,
                poly_no_ask=p_no,
                gross_spread=gross,
                net_edge=net,
                settlement_match_score=match,
                settlement_flags=flags,
                volume_kalshi=float(12_000 + (i * 791) % 90_000),
                volume_poly=float(8_000 + (i * 613) % 75_000),
                category=_CATEGORIES[i % len(_CATEGORIES)],
                kelly_fraction=min(round(net * 8.0, 3), 0.45),
                detection_ts=_NOW - timedelta(seconds=30 * i),
            )
        )
    return sorted(out, key=lambda o: -o.net_edge)


def generate_demo_proposal_events(count: int = 32) -> list[AuditEvent]:
    """Audit rows surfaced as /proposals in the terminal cache."""
    symbols = ("NVDA", "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "AMD", "SMH", "SPY")
    events: list[AuditEvent] = []
    for i in range(count):
        sym = symbols[i % len(symbols)]
        direction = "LONG" if i % 3 != 0 else "SHORT"
        conviction = round(0.55 + (i % 40) * 0.01, 2)
        entry = round(100.0 + i * 3.7, 2)
        events.append(
            AuditEvent(
                event_type=EventType.PROPOSAL_CREATED,
                symbol=sym,
                conviction=conviction,
                raw_payload={
                    "direction": direction,
                    "instrument": "EQUITY" if i % 5 else "OPTIONS",
                    "entry_price": entry,
                    "stop_loss": round(entry * (0.97 if direction == "LONG" else 1.03), 2),
                    "take_profit": round(entry * (1.06 if direction == "LONG" else 0.94), 2),
                    "conviction_final": conviction,
                    "demo_mode": True,
                    "proposal_index": i,
                },
            )
        )
    return events
