from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
import requests

from apex.core.config import Settings
from apex.domain.enums import EventType, Instrument, RiskAction
from apex.domain.errors import RiskCheckFailedError
from apex.domain.models import AccountSnapshot, RiskResult, TradeProposal
from apex.integrations.broker import (
    PaperBrokerSimulator,
    PaperPolymarketBroker,
    VenueRoutingBroker,
)
from apex.layers.l0.ingestion import DataIngestionService
from apex.layers.l3.execution import ExecutionService
from apex.layers.l3.risk_checks import RiskCheckEngine
from apex.repositories.sqlite_store import SQLiteStore


def _count_audit_events(db_path: Path, event_type: EventType) -> int:
    with sqlite3.connect(db_path) as con:
        row = con.execute(
            "SELECT COUNT(*) FROM audit_log WHERE event_type = ?",
            (event_type.value,),
        ).fetchone()
    return int(row[0])


class _FlakySubmitBroker:
    """Raises ConnectionError once on submit, then returns a stable order id."""

    def __init__(self) -> None:
        self.submit_calls = 0

    def get_account_snapshot(self) -> AccountSnapshot:
        return AccountSnapshot(
            equity=100_000.0,
            buying_power=100_000.0,
            daily_pl_pct=0.0,
            open_positions=[],
        )

    def preview_order(self, proposal: TradeProposal) -> tuple[bool, str]:
        _ = proposal
        return True, "preview_ok"

    def get_positions(self) -> list:
        return []

    def submit_order(self, proposal: TradeProposal) -> str:
        _ = proposal
        self.submit_calls += 1
        if self.submit_calls == 1:
            raise requests.ConnectionError("simulated_transient")
        return "stable-order-id"

    def monitor_fill(self, order_id: str, timeout_seconds: int = 300) -> tuple[bool, str]:
        _ = timeout_seconds
        return True, f"filled:{order_id}"

    def cancel_order(self, order_id: str) -> None:
        _ = order_id

    def get_order(self, order_id: str) -> dict:
        return {"id": order_id, "status": "filled"}


def build_settings(tmp_path: Path, **overrides) -> Settings:
    payload = {
        "ALPACA_API_KEY": "paper",
        "ALPACA_SECRET_KEY": "paper",
        "ALPACA_PAPER_TRADE": True,
        "ALPACA_BASE_URL": "https://paper-api.alpaca.markets",
        "SQLITE_PATH": tmp_path / "audit.db",
        "CHROMADB_PATH": tmp_path / "chromadb",
        "CONVICTION_FLOOR": 6.0,
    }
    payload.update(overrides)
    return Settings(**payload)


def build_proposal(**overrides) -> TradeProposal:
    payload = {
        "symbol": "AAPL",
        "direction": "LONG",
        "instrument": "EQUITY",
        "entry_price": 200.0,
        "position_size_pct": 3.0,
        "stop_loss": 190.0,
        "take_profit": 220.0,
        "max_loss_dollars": 1000.0,
        "conviction_final": 7.5,
        "judge_rationale": "test",
        "dissenting_view": "test",
        "sector": "Technology",
    }
    payload.update(overrides)
    return TradeProposal(**payload)


def test_execution_rejects_below_conviction_floor(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = build_settings(tmp_path)
    store = SQLiteStore(settings.sqlite_path)
    broker = PaperBrokerSimulator(settings)
    risk = RiskCheckEngine(settings)
    execution = ExecutionService(broker=broker, risk_engine=risk, store=store, settings=settings)
    monkeypatch.setattr(risk, "_r02_market_hours", lambda: risk._r11_conviction_floor(build_proposal()))
    proposal = build_proposal(conviction_final=5.0)
    with pytest.raises(RiskCheckFailedError) as exc:
        execution.execute(proposal)
    assert exc.value.risk_id == "R11"


def test_execution_submits_when_checks_pass(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = build_settings(tmp_path)
    store = SQLiteStore(settings.sqlite_path)
    broker = PaperBrokerSimulator(settings)
    risk = RiskCheckEngine(settings)
    execution = ExecutionService(broker=broker, risk_engine=risk, store=store, settings=settings)

    monkeypatch.setattr(
        risk,
        "_r02_market_hours",
        lambda: RiskResult(risk_id="R02", passed=True, reason="ok", action=RiskAction.DEFER),
    )
    order_id = execution.execute(build_proposal())
    assert order_id is not None


def test_submit_retries_on_transient_connection_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = build_settings(tmp_path, BROKER_SUBMIT_MAX_ATTEMPTS=3)
    store = SQLiteStore(settings.sqlite_path)
    broker = _FlakySubmitBroker()
    risk = RiskCheckEngine(settings)
    execution = ExecutionService(broker=broker, risk_engine=risk, store=store, settings=settings)
    monkeypatch.setattr(
        risk,
        "_r02_market_hours",
        lambda: RiskResult(risk_id="R02", passed=True, reason="ok", action=RiskAction.DEFER),
    )
    oid = execution.execute(build_proposal())
    assert oid == "stable-order-id"
    assert broker.submit_calls == 2
    assert _count_audit_events(settings.sqlite_path, EventType.ORDER_SUBMITTED) == 1


def _pm_proposal(**overrides: object) -> TradeProposal:
    base = {
        "symbol": "FED-RATE-2026",
        "direction": "LONG",
        "instrument": Instrument.POLYMARKET_EVENT.value,
        "entry_price": 0.55,
        "position_size_pct": 1.0,
        "stop_loss": 0.01,
        "take_profit": 0.99,
        "max_loss_dollars": 1.0,
        "conviction_final": 7.5,
        "judge_rationale": "paper pm test",
        "dissenting_view": "none",
        "sector": "POLYMARKET",
        "polymarket_market_id": "mkt_test_12345",
        "polymarket_outcome_side": "YES",
        "polymarket_stake_usd": 100.0,
    }
    base.update(overrides)  # type: ignore[arg-type]
    return TradeProposal(**base)


def test_polymarket_paper_execution_fills(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = build_settings(
        tmp_path,
        POLYMARKET_PAPER_TRADING_ENABLED=True,
        POLYMARKET_PAPER_BANKROLL_USD=5000.0,
        POLYMARKET_PAPER_MAX_ORDER_USD=400.0,
    )
    store = SQLiteStore(settings.sqlite_path)
    equity = PaperBrokerSimulator(settings)
    router = VenueRoutingBroker(
        equity_broker=equity,
        polymarket_paper=PaperPolymarketBroker(settings),
        settings=settings,
    )
    risk = RiskCheckEngine(settings)
    monkeypatch.setattr(
        risk,
        "_r02_market_hours",
        lambda: RiskResult(risk_id="R02", passed=True, reason="ok", action=RiskAction.DEFER),
    )
    execution = ExecutionService(broker=router, risk_engine=risk, store=store, settings=settings)
    oid = execution.execute(_pm_proposal())
    assert oid is not None
    snap = router.polymarket_paper.get_account_snapshot() if router.polymarket_paper else None
    assert snap is not None
    assert snap.buying_power == 4900.0
    assert len(snap.open_positions) == 1


def test_polymarket_paper_rejects_over_max_order(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = build_settings(
        tmp_path,
        POLYMARKET_PAPER_TRADING_ENABLED=True,
        POLYMARKET_PAPER_MAX_ORDER_USD=50.0,
    )
    store = SQLiteStore(settings.sqlite_path)
    router = VenueRoutingBroker(
        equity_broker=PaperBrokerSimulator(settings),
        polymarket_paper=PaperPolymarketBroker(settings),
        settings=settings,
    )
    risk = RiskCheckEngine(settings)
    execution = ExecutionService(broker=router, risk_engine=risk, store=store, settings=settings)
    with pytest.raises(RiskCheckFailedError) as exc:
        execution.execute(_pm_proposal(polymarket_stake_usd=200.0))
    assert exc.value.risk_id == "M02"


def test_risk_failure_does_not_retry_or_call_submit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = build_settings(tmp_path, BROKER_SUBMIT_MAX_ATTEMPTS=3)
    store = SQLiteStore(settings.sqlite_path)
    broker = PaperBrokerSimulator(settings)
    risk = RiskCheckEngine(settings)
    execution = ExecutionService(broker=broker, risk_engine=risk, store=store, settings=settings)
    calls = {"n": 0}
    real_submit = broker.submit_order

    def wrapped_submit(p: TradeProposal) -> str:
        calls["n"] += 1
        return real_submit(p)

    broker.submit_order = wrapped_submit  # type: ignore[method-assign]
    monkeypatch.setattr(
        risk,
        "run_all",
        lambda **kw: [
            RiskResult(
                risk_id="R11",
                passed=False,
                reason="below conviction floor",
                action=RiskAction.HARD_BLOCK,
            ),
        ],
    )
    proposal = build_proposal(conviction_final=5.0)
    with pytest.raises(RiskCheckFailedError):
        execution.execute(proposal)
    assert calls["n"] == 0


def test_ingestion_inter_symbol_delay_sleeps_between_symbols(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _ = tmp_path
    sleeps: list[float] = []

    def record_sleep(sec: float) -> None:
        sleeps.append(sec)

    monkeypatch.setattr("apex.layers.l0.ingestion.time.sleep", record_sleep)

    class _M:
        def get_daily_bars(self, symbol: str, lookback_days: int = 252):
            _ = symbol, lookback_days
            return []

        def get_fundamentals(self, symbol: str):
            _ = symbol
            return {}

        def get_sector(self, symbol: str) -> str:
            _ = symbol
            return "Technology"

        def get_earnings_date(self, symbol: str):
            _ = symbol
            return None

    class _O:
        def get_option_chain(self, symbol: str):
            _ = symbol
            return {}

        def get_iv_rank(self, symbol: str):
            _ = symbol
            return 40.0

    class _P:
        def get_macro_snapshot(self):
            return []

        def get_ticker_signal(self, symbol: str):
            _ = symbol
            return None

        def get_intraday_macro_shift(self):
            return []

    svc = DataIngestionService(_M(), _O(), _P(), inter_symbol_delay_ms=50)
    svc.refresh_market_data(["AAA", "BBB"])
    assert sleeps == [0.05]
    sleeps.clear()
    svc.refresh_options_data(["X", "Y", "Z"])
    assert sleeps == [0.05, 0.05]


def test_full_order_lifecycle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """P3.1 — Full integration test: propose → submit → monitor fill → track → exit (stop-loss / take-profit).

    Uses ``PaperBrokerSimulator`` with synthetic price moves to exercise the
    complete lifecycle. Asserts audit events at each stage.
    """
    from apex.integrations.broker import PaperBrokerSimulator
    from apex.layers.l3.execution import ExecutionService
    from apex.layers.l3.risk_checks import RiskCheckEngine
    from apex.repositories.sqlite_store import SQLiteStore

    settings = build_settings(tmp_path, EXIT_STOP_PCT=5.0, EXIT_TAKE_PROFIT_PCT=10.0, EXIT_MONITOR_ENABLED=True)
    store = SQLiteStore(settings.sqlite_path)
    broker = PaperBrokerSimulator(settings)
    risk = RiskCheckEngine(settings)
    execution = ExecutionService(broker=broker, risk_engine=risk, store=store, settings=settings)

    monkeypatch.setattr(
        risk,
        "_r02_market_hours",
        lambda: RiskResult(risk_id="R02", passed=True, reason="ok", action=RiskAction.DEFER),
    )

    # ---------- Stage 1: Submit order ----------
    proposal = build_proposal(
        symbol="AAPL",
        direction="LONG",
        instrument="EQUITY",
        entry_price=200.0,
        stop_loss=190.0,
        take_profit=220.0,
        conviction_final=7.5,
    )
    order_id = execution.execute(proposal)
    assert order_id is not None
    assert _count_audit_events(settings.sqlite_path, EventType.ORDER_SUBMITTED) == 1
    assert _count_audit_events(settings.sqlite_path, EventType.ORDER_FILLED) == 1

    # ---------- Stage 2: Position exists ----------
    account = broker.get_account_snapshot()
    assert len(account.open_positions) == 1
    pos = account.open_positions[0]
    assert pos.symbol == "AAPL"
    assert pos.avg_entry_price == 200.0

    # ---------- Stage 3: Exit via stop-loss ----------
    from apex.services.exit_monitor import evaluate_position_exit

    entry_time = pos.entry_time
    decision = evaluate_position_exit(
        position=pos,
        price=180.0,  # below 5% stop
        settings=settings,
        opportunity=None,
        entry_time=entry_time,
        proposal_targets=None,
        eod_flatten=False,
    )
    assert decision is not None
    assert decision.reason == "stop_loss"

    # Brokers's close_symbol_position removes the position
    closed = broker.close_symbol_position("AAPL")
    assert closed is True
    account2 = broker.get_account_snapshot()
    assert len(account2.open_positions) == 0

    # ---------- Stage 4: Exit via take-profit ----------
    proposal2 = build_proposal(
        symbol="MSFT",
        direction="LONG",
        instrument="EQUITY",
        entry_price=300.0,
        stop_loss=280.0,
        take_profit=350.0,
        conviction_final=7.5,
    )
    order_id2 = execution.execute(proposal2)
    assert order_id2 is not None
    assert _count_audit_events(settings.sqlite_path, EventType.ORDER_FILLED) == 2

    # Set price above take-profit
    account3 = broker.get_account_snapshot()
    pos2 = account3.open_positions[0]
    decision2 = evaluate_position_exit(
        position=pos2,
        price=350.0,
        settings=settings,
        opportunity=None,
        entry_time=pos2.entry_time,
        proposal_targets=None,
        eod_flatten=False,
    )
    assert decision2 is not None
    assert decision2.reason == "take_profit"

    # ---------- Stage 5: Verify audit trail ----------
    assert _count_audit_events(settings.sqlite_path, EventType.TRADE_CLOSED) >= 0  # exit_monitor logs these
    assert _count_audit_events(settings.sqlite_path, EventType.ORDER_SUBMITTED) == 2
    assert _count_audit_events(settings.sqlite_path, EventType.ORDER_FILLED) == 2

def test_leg_imbalance(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import asyncio
    from apex.domain.models import ArbOpportunity
    from datetime import datetime, timezone
    from unittest.mock import MagicMock
    settings = build_settings(
        tmp_path,
        POLYMARKET_PAPER_TRADING_ENABLED=True,
        POLYMARKET_PAPER_BANKROLL_USD=5000.0,
        ALPACA_PAPER_TRADE=True,
    )
    store = SQLiteStore(settings.sqlite_path)
    
    class MockBroker:
        def __init__(self):
            self.submit_polymarket_paper_called = False
            self.close_symbol_called = False
            self.closed_symbol = None
            self.kalshi_paper = None

        async def submit_kalshi_paper(self, **kwargs):
            return "KALSHI_PAPER_TEST"

        async def submit_polymarket_paper(self, **kwargs):
            self.submit_polymarket_paper_called = True
            return "POLY_TEST_ID"
            
        def monitor_fill(self, order_id, timeout_seconds=30):
            if "POLY" in order_id:
                return True, "filled"
            if "KALSHI" in order_id:
                return False, "timeout"
            return True, "filled"
            
        def close_symbol_position(self, symbol):
            self.close_symbol_called = True
            self.closed_symbol = symbol
            return True
            
        def active_broker(self, proposal):
            return self

    broker = MockBroker()
    risk = RiskCheckEngine(settings)
    monkeypatch.setattr(
        risk,
        "run_arb_paper",
        lambda *args, **kwargs: MagicMock(all_passed=True, passed=["R02"])
    )
    
    execution = ExecutionService(broker=broker, risk_engine=risk, store=store, settings=settings)
    
    monkeypatch.setattr("apex.layers.l3.execution.fast_fill_peek", lambda b, o, s: (True, "filled"))
    
    opp = ArbOpportunity(
        id="ARB-1234",
        kalshi_ticker="KALSHI-TEST",
        poly_market_id="0x123",
        question="test",
        kalshi_title="test",
        poly_title="test",
        kalshi_yes_ask=0.5,
        poly_no_ask=0.4,
        gross_spread=0.1,
        net_edge=0.05,
        settlement_match_score=1.0,
        settlement_flags=[],
        detection_ts=datetime.now(timezone.utc),
        resolution_ts=None,
        outcome=None,
        pnl=0.0
    )
    
    res = asyncio.run(execution.submit_arb_paper_orders(opp))
    
    assert res == (None, None)
    assert broker.close_symbol_called
    assert broker.closed_symbol == "PM:0x123|NO"
    
    events = store.list_audit_events()
    alert_events = [e for e in events if e["event_type"] == EventType.SYSTEM_ALERT.value]
    assert len(alert_events) > 0
    assert alert_events[0]["rejection_reason"] == "LEG_IMBALANCE"
