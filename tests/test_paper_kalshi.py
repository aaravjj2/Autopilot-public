"""PaperKalshiBroker and VenueRoutingBroker arb helpers (Phase 1)."""

from __future__ import annotations

import asyncio


from apex.core.config import Settings
from apex.integrations.broker import PaperKalshiBroker, PaperPolymarketBroker, VenueRoutingBroker
from apex.integrations.broker import PaperBrokerSimulator


def test_paper_kalshi_submit_and_fill(tmp_path):
    settings = Settings(
        SQLITE_PATH=tmp_path / "audit.db",
        ALPACA_PAPER_TRADE=True,
        KALSHI_PAPER_BANKROLL_USD=1000.0,
        POLYMARKET_PAPER_TRADING_ENABLED=True,
        POLYMARKET_PAPER_BANKROLL_USD=1000.0,
    )
    kalshi = PaperKalshiBroker(settings)
    oid = kalshi.submit_yes_leg("KX-TEST", 50.0, 0.45)
    filled, reason = kalshi.monitor_fill(oid, 5)
    assert filled
    assert "filled" in reason


def test_venue_routing_submit_methods(tmp_path):
    settings = Settings(
        SQLITE_PATH=tmp_path / "audit.db",
        ALPACA_PAPER_TRADE=True,
        POLYMARKET_PAPER_TRADING_ENABLED=True,
        POLYMARKET_PAPER_BANKROLL_USD=500.0,
        KALSHI_PAPER_BANKROLL_USD=500.0,
    )
    broker = VenueRoutingBroker(
        equity_broker=PaperBrokerSimulator(settings),
        polymarket_paper=PaperPolymarketBroker(settings),
        kalshi_paper=PaperKalshiBroker(settings),
        settings=settings,
    )
    k_id = asyncio.run(broker.submit_kalshi_paper("KX-T", 25.0, 0.4))
    p_id = asyncio.run(broker.submit_polymarket_paper("tok123", "NO", 25.0, 0.5))
    assert k_id
    assert p_id
