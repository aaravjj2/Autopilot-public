from __future__ import annotations

from pathlib import Path

from apex.domain.models import ArbOpportunity
from apex.repositories.sqlite_store import SQLiteStore


def test_list_active_arb_opportunities_clamps_limit(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "arb.db")
    rows = [
        ArbOpportunity(
            id="a",
            kalshi_ticker="K-A",
            poly_market_id="P-A",
            question="Q",
            kalshi_title="Q",
            poly_title="Q",
            kalshi_yes_ask=0.4,
            poly_no_ask=0.5,
            gross_spread=0.1,
            net_edge=0.04,
            settlement_match_score=0.8,
            settlement_flags=[],
            volume_kalshi=1000,
            volume_poly=1000,
            category="macro",
            kelly_fraction=0.1,
        ),
        ArbOpportunity(
            id="b",
            kalshi_ticker="K-B",
            poly_market_id="P-B",
            question="Q2",
            kalshi_title="Q2",
            poly_title="Q2",
            kalshi_yes_ask=0.4,
            poly_no_ask=0.5,
            gross_spread=0.1,
            net_edge=0.03,
            settlement_match_score=0.8,
            settlement_flags=[],
            volume_kalshi=1000,
            volume_poly=1000,
            category="macro",
            kelly_fraction=0.1,
        ),
    ]
    store.save_arb_opportunities(rows)
    out = store.list_active_arb_opportunities(limit=0)
    assert len(out) == 1
    assert out[0]["id"] == "a"
