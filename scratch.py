import asyncio
from unittest.mock import MagicMock
from apex.core.config import Settings
from apex.layers.l3.execution import ExecutionService, fast_fill_peek
from apex.domain.models import ArbOpportunity
from datetime import datetime, timezone
import logging

logging.basicConfig(level=logging.DEBUG)

class MockBroker:
    def __init__(self):
        pass
    async def submit_polymarket_paper(self, **kwargs):
        return "POLY_TEST_ID"
    def monitor_fill(self, order_id, timeout_seconds=30):
        print(f"MockBroker.monitor_fill called with {order_id}")
        if "POLY" in order_id:
            return True, "filled"
        if "KALSHI" in order_id:
            return False, "timeout"
        return True, "filled"
    def get_account_snapshot(self):
        return MagicMock()

async def run():
    settings = Settings(ALPACA_API_KEY="paper", ALPACA_SECRET_KEY="paper", ALPACA_PAPER_TRADE=True, POLYMARKET_PAPER_TRADING_ENABLED=True, POLYMARKET_PAPER_BANKROLL_USD=5000.0)
    broker = MockBroker()
    risk = MagicMock()
    risk.run_arb_paper.return_value = MagicMock(all_passed=True, passed=["R02"])
    store = MagicMock()
    
    execution = ExecutionService(broker=broker, risk_engine=risk, store=store, settings=settings)
    
    opp = ArbOpportunity(
        id="ARB-1234", kalshi_ticker="KALSHI-TEST", poly_market_id="0x123", question="test",
        kalshi_title="test", poly_title="test", kalshi_yes_ask=0.5, poly_no_ask=0.4, gross_spread=0.1,
        net_edge=0.05, settlement_match_score=1.0, settlement_flags=[], detection_ts=datetime.now(timezone.utc),
        resolution_ts=None, outcome=None, pnl=0.0
    )
    
    res = await execution.submit_arb_paper_orders(opp)
    print("RES:", res)

asyncio.run(run())
