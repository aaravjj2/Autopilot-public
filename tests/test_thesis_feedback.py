from __future__ import annotations


from apex.domain.models import ArbOpportunity
from apex.repositories.sqlite_store import SQLiteStore
from apex.core.config import Settings
from apex.layers.l2.arb_analyst_panel import ArbAnalystPanel

def test_get_failed_thesis_examples(tmp_path):
    store = SQLiteStore(tmp_path / "test.db")

    # 1. Store opp with LOSS and SAFE
    opp1 = ArbOpportunity(
        kalshi_ticker="TICK-1",
        poly_market_id="POLY-1",
        question="Q1",
        kalshi_title="Title1",
        poly_title="Title1 Poly",
        kalshi_yes_ask=0.5,
        poly_no_ask=0.4,
        gross_spread=0.1,
        net_edge=0.05,
        settlement_match_score=0.9,
        settlement_flags=[],
        outcome="LOSS",
        pnl=-100.0
    )
    # inject the attribute before saving
    setattr(opp1, "thesis_settlement_verdict", "SAFE")

    # 2. Store opp with WIN and SAFE
    opp2 = ArbOpportunity(
        kalshi_ticker="TICK-2",
        poly_market_id="POLY-2",
        question="Q2",
        kalshi_title="Title2",
        poly_title="Title2 Poly",
        kalshi_yes_ask=0.5,
        poly_no_ask=0.4,
        gross_spread=0.1,
        net_edge=0.05,
        settlement_match_score=0.9,
        settlement_flags=[],
        outcome="WIN",
        pnl=100.0
    )
    setattr(opp2, "thesis_settlement_verdict", "SAFE")

    # 3. Store opp with LOSS and CAUTION
    opp3 = ArbOpportunity(
        kalshi_ticker="TICK-3",
        poly_market_id="POLY-3",
        question="Q3",
        kalshi_title="Title3",
        poly_title="Title3 Poly",
        kalshi_yes_ask=0.5,
        poly_no_ask=0.4,
        gross_spread=0.1,
        net_edge=0.05,
        settlement_match_score=0.9,
        settlement_flags=[],
        outcome="LOSS",
        pnl=-50.0
    )
    setattr(opp3, "thesis_settlement_verdict", "CAUTION")

    store.save_arb_opportunities([opp1, opp2, opp3])

    # Fetch failed examples
    failed = store.get_failed_thesis_examples()
    assert len(failed) == 1
    assert failed[0].kalshi_ticker == "TICK-1"
    assert getattr(failed[0], "thesis_settlement_verdict") == "SAFE"

    # Test the injection into panel
    # We won't test the actual LLM call, but we can verify the prompt generation
    # indirectly or just make sure there are no errors when constructing panel
    settings = Settings(sqlite_path=tmp_path / "test.db")
    panel = ArbAnalystPanel(settings)
    assert panel is not None
