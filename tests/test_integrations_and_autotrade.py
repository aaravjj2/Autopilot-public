from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from apex.core.config import Settings
from apex.domain.enums import Direction, Instrument, PMSignal, RiskAction
from apex.domain.models import OpportunityScore, RiskResult, TradeProposal
from apex.integrations.broker import PaperBrokerSimulator
from apex.integrations.repo_registry import IntegrationRegistry
from apex.layers.l0.ingestion import DataIngestionService
from apex.layers.l1.brain import FinanceBrainService
from apex.layers.l2.agent_panel import MultiAgentPanelService
from apex.layers.l3.execution import ExecutionService
from apex.layers.l3.risk_checks import RiskCheckEngine
from apex.layers.l4.observability import ObservabilityService
from apex.repositories.sqlite_store import SQLiteStore
from apex.services.engine import ApexEngine


class _MarketStub:
    def get_intraday_price(self, symbol: str) -> float:
        _ = symbol
        return 100.0

    def get_daily_bars(self, symbol: str, lookback_days: int = 252):
        _ = symbol, lookback_days
        return [{"date": "2026-01-01", "open": 100.0, "high": 102.0, "low": 98.0, "close": 101.0, "volume": 2_000_000}] * 40

    def get_fundamentals(self, symbol: str):
        _ = symbol
        return {"pe": 20.0, "revenue_growth": 0.1, "analyst_recommendation": "buy"}

    def get_sector(self, symbol: str) -> str:
        return "Technology" if symbol != "JPM" else "Financial Services"

    def get_earnings_date(self, symbol: str):
        _ = symbol
        return None


class _OptionsStub:
    def get_option_chain(self, symbol: str):
        _ = symbol
        return {"calls": [], "puts": [], "put_call_oi_ratio": 1.0, "put_call_volume_ratio": 1.0}

    def get_iv_rank(self, symbol: str):
        _ = symbol
        return 45.0


class _PMStub:
    def get_macro_snapshot(self):
        return [{"market": "Fed", "probability": 0.4}]

    def get_ticker_signal(self, symbol: str):
        _ = symbol
        return {"signal": "BULLISH", "divergence": 0.2, "whale_alignment": 0.6}

    def get_intraday_macro_shift(self):
        return []


def _settings(tmp_path: Path, **overrides) -> Settings:
    payload = {
        "ALPACA_API_KEY": "paper",
        "ALPACA_SECRET_KEY": "paper",
        "ALPACA_PAPER_TRADE": True,
        "ALPACA_BASE_URL": "https://paper-api.alpaca.markets",
        "SQLITE_PATH": tmp_path / "audit.db",
        "CHROMADB_PATH": tmp_path / "chromadb",
    }
    payload.update(overrides)
    return Settings(**payload)


def _engine(tmp_path: Path, autotrade_all_approved: bool) -> ApexEngine:
    settings = _settings(tmp_path, AUTOTRADE_ALL_APPROVED=autotrade_all_approved)
    store = SQLiteStore(settings.sqlite_path)
    ingestion = DataIngestionService(_MarketStub(), _OptionsStub(), _PMStub())
    brain = FinanceBrainService(settings, _PMStub())
    panel = MultiAgentPanelService()
    broker = PaperBrokerSimulator(settings)
    risk = RiskCheckEngine(settings)
    execution = ExecutionService(broker=broker, risk_engine=risk, store=store, settings=settings)
    obs = ObservabilityService(store=store)
    registry = IntegrationRegistry(settings)
    from apex.services.arb_engine import ArbEngine
    arb = ArbEngine(settings=settings, store=store)
    return ApexEngine(
        settings=settings,
        store=store,
        ingestion=ingestion,
        brain=brain,
        panel=panel,
        execution=execution,
        observability=obs,
        integration_registry=registry,
        arb_engine=arb,
    )


def _opportunity(symbol: str) -> OpportunityScore:
    return OpportunityScore(
        symbol=symbol,
        direction=Direction.LONG,
        instrument=Instrument.EQUITY,
        conviction=7.0,
        technical_score=7.0,
        fundamental_score=6.5,
        pm_signal=PMSignal.BULLISH,
        pm_divergence=0.2,
        catalyst="test",
        risk_reward=1.8,
        options_structure=None,
        max_position_pct=5.0,
        invalidation="test",
    )


def test_integration_registry_strict_mode_blocks_missing_required(tmp_path: Path) -> None:
    settings = _settings(
        tmp_path,
        ALPACA_API_KEY="",
        ALPACA_SECRET_KEY="",
        STRICT_INTEGRATIONS=True,
    )
    registry = IntegrationRegistry(settings)
    with pytest.raises(RuntimeError):
        registry.validate(strict=True)


def test_integration_registry_non_strict_allows_missing(tmp_path: Path) -> None:
    settings = _settings(
        tmp_path,
        ALPACA_API_KEY="",
        ALPACA_SECRET_KEY="",
        STRICT_INTEGRATIONS=False,
    )
    registry = IntegrationRegistry(settings)
    payload = registry.validate(strict=False)
    assert payload["strict_mode"] is False
    assert payload["missing_required"]


def test_autotrade_all_approved_submits_full_batch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    engine = _engine(tmp_path, autotrade_all_approved=True)
    symbols = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META"]
    for symbol in symbols:
        engine.ingestion.cache.market[symbol] = {
            "bars": [{"close": 100.0, "low": 98.0, "high": 102.0}],
            "fundamentals": {},
            "sector": "Technology",
            "earnings_date": None,
        }
        engine.ingestion.cache.options[symbol] = {"iv_rank": 40.0}
    monkeypatch.setattr(engine.execution.risk_engine, "_r02_market_hours", lambda: engine.execution.risk_engine._r14_alpaca_preview(True, "ok"))
    proposals = engine.agent_panel_run([_opportunity(symbol) for symbol in symbols])
    assert len(proposals) == len(symbols)


def test_autotrade_disabled_respects_top_symbols_limit(tmp_path: Path) -> None:
    engine = _engine(tmp_path, autotrade_all_approved=False)
    symbols = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META"]
    for symbol in symbols:
        engine.ingestion.cache.market[symbol] = {
            "bars": [{"close": 100.0, "low": 98.0, "high": 102.0}],
            "fundamentals": {},
            "sector": "Technology",
            "earnings_date": None,
        }
        engine.ingestion.cache.options[symbol] = {"iv_rank": 40.0}
    proposals = engine.agent_panel_run([_opportunity(symbol) for symbol in symbols])
    assert len(proposals) == engine.settings.top_symbols_per_day


def _trade_proposal_stub() -> TradeProposal:
    return TradeProposal(
        symbol="AAPL",
        direction=Direction.LONG,
        instrument=Instrument.EQUITY,
        entry_price=200.0,
        position_size_pct=3.0,
        stop_loss=190.0,
        take_profit=220.0,
        max_loss_dollars=1000.0,
        conviction_final=8.0,
        judge_rationale="t",
        dissenting_view="t",
        sector="Technology",
    )


def test_order_submission_audit_includes_error_class_on_risk_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = _engine(tmp_path, autotrade_all_approved=True)
    monkeypatch.setattr(
        engine.execution.risk_engine,
        "run_all",
        lambda **kw: [
            RiskResult(
                risk_id="R11",
                passed=False,
                reason="below floor",
                action=RiskAction.HARD_BLOCK,
            ),
        ],
    )
    engine.order_submission([_trade_proposal_stub()])
    with sqlite3.connect(engine.settings.sqlite_path) as con:
        row = con.execute(
            """
            SELECT raw_payload FROM audit_log
            WHERE json_extract(raw_payload, '$.phase') = 'order_submission'
            ORDER BY rowid DESC LIMIT 1
            """
        ).fetchone()
    assert row is not None
    payload = json.loads(row[0])
    assert payload.get("error_class") == "RiskCheckFailedError"


def test_fill_reconciliation_detects_non_filled_status(tmp_path: Path) -> None:
    engine = _engine(tmp_path, autotrade_all_approved=True)

    def fake_get_order(order_id: str) -> dict:
        return {"id": order_id, "status": "accepted"}

    engine.execution.broker.get_order = fake_get_order  # type: ignore[method-assign]
    engine.todays_order_ids = ["ord-123"]
    engine.fill_reconciliation()
    with sqlite3.connect(engine.settings.sqlite_path) as con:
        row = con.execute(
            """
            SELECT raw_payload FROM audit_log
            WHERE json_extract(raw_payload, '$.phase') = 'fill_reconciliation'
            ORDER BY rowid DESC LIMIT 1
            """
        ).fetchone()
    assert row is not None
    payload = json.loads(row[0])
    assert payload["discrepancies"]
    assert payload["discrepancies"][0].get("issue") == "status_not_filled"
