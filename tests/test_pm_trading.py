"""Kalshi / Polymarket paper agents and single-leg trades."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from apex.core.config import Settings
from apex.domain.models import ArbOpportunity
from apex.integrations.broker import PaperKalshiBroker, PaperPolymarketBroker, PaperBrokerSimulator, VenueRoutingBroker
from apex.layers.l3.execution import ExecutionService
from apex.layers.l3.risk_checks import RiskCheckEngine
from apex.main import build_engine
from apex.repositories.sqlite_store import SQLiteStore
from apex.services.pm_trading import (
    place_kalshi_paper_leg,
    place_polymarket_paper_leg,
    pm_agents_status,
    run_polymarket_agent_cycle,
    run_kalshi_arb_agent_cycle,
)


def _settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv("KALSHI_DEMO_TRADING_ENABLED", "false")
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "audit.db"))
    return Settings(
        sqlite_path=tmp_path / "audit.db",
        alpaca_paper_trade=True,
        polymarket_paper_trading_enabled=True,
        polymarket_automated_events_enabled=False,
        kalshi_demo_trading_enabled=False,
        kalshi_paper_bankroll_usd=5000.0,
        polymarket_paper_bankroll_usd=5000.0,
        polymarket_paper_max_order_usd=500.0,
        arb_paper_relax_orderbook=True,
        arb_min_net_edge=0.01,
        kalshi_min_volume_24h=0.0,
    )


@pytest.mark.asyncio
async def test_kalshi_paper_leg_writes_audit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = _settings(tmp_path, monkeypatch)
    store = SQLiteStore(cfg.sqlite_path)
    equity = PaperBrokerSimulator(cfg)
    router = VenueRoutingBroker(
        equity_broker=equity,
        polymarket_paper=PaperPolymarketBroker(cfg),
        kalshi_paper=PaperKalshiBroker(cfg),
        settings=cfg,
    )
    execution = ExecutionService(
        broker=router,
        risk_engine=RiskCheckEngine(cfg),
        store=store,
        settings=cfg,
    )

    engine = SimpleNamespace(settings=cfg, store=store, execution=execution)

    out = await place_kalshi_paper_leg(
        engine,  # type: ignore[arg-type]
        ticker="KX-TEST",
        stake_usd=25.0,
        price=0.55,
        question="Test market",
    )
    assert out["status"] == "ok"
    assert out["order_id"]
    rows = store.read_table("audit_log", limit=20)
    filled = [r for r in rows if r.get("event_type") == "ORDER_FILLED"]
    assert any("kalshi_paper" in str(r.get("raw_payload")) for r in filled)


@pytest.mark.asyncio
async def test_polymarket_paper_leg_writes_audit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = _settings(tmp_path, monkeypatch)
    store = SQLiteStore(cfg.sqlite_path)
    router = VenueRoutingBroker(
        equity_broker=PaperBrokerSimulator(cfg),
        polymarket_paper=PaperPolymarketBroker(cfg),
        kalshi_paper=PaperKalshiBroker(cfg),
        settings=cfg,
    )
    execution = ExecutionService(
        broker=router,
        risk_engine=RiskCheckEngine(cfg),
        store=store,
        settings=cfg,
    )

    engine = SimpleNamespace(settings=cfg, store=store, execution=execution)

    out = await place_polymarket_paper_leg(
        engine,  # type: ignore[arg-type]
        market_id="mkt-test-1",
        outcome="YES",
        stake_usd=40.0,
        price=0.45,
    )
    assert out["status"] == "ok"
    rows = store.read_table("audit_log", limit=20)
    assert any("polymarket_paper" in str(r.get("raw_payload")) for r in rows)


@pytest.mark.asyncio
async def test_prediction_markets_cycle_runs_both(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = _settings(tmp_path, monkeypatch)
    store = SQLiteStore(cfg.sqlite_path)
    router = VenueRoutingBroker(
        equity_broker=PaperBrokerSimulator(cfg),
        polymarket_paper=PaperPolymarketBroker(cfg),
        kalshi_paper=PaperKalshiBroker(cfg),
        settings=cfg,
    )
    execution = ExecutionService(
        broker=router,
        risk_engine=RiskCheckEngine(cfg),
        store=store,
        settings=cfg,
    )
    engine = SimpleNamespace(settings=cfg, store=store, execution=execution)

    monkeypatch.setattr("apex.services.arb_scan.scan_and_persist", lambda *a, **k: [])
    engine.polymarket_event_discovery = lambda: []  # type: ignore[attr-defined]
    engine.polymarket_paper_order_submission = lambda proposals: []  # type: ignore[attr-defined]

    from apex.services.pm_trading import run_prediction_markets_agent_cycle

    out = await run_prediction_markets_agent_cycle(engine)  # type: ignore[arg-type]
    assert out["status"] == "ok"
    assert "polymarket" in out
    assert "kalshi_arb" in out


@pytest.mark.asyncio
async def test_kalshi_agent_uses_cached_when_scan_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = _settings(tmp_path, monkeypatch)
    cfg = cfg.model_copy(update={"kalshi_agent_use_cached_opps": True, "pm_agent_fast_scan": True})
    store = SQLiteStore(cfg.sqlite_path)
    opp = ArbOpportunity(
        id="agent-cache",
        kalshi_ticker="KX-AGENT",
        poly_market_id="0xagent",
        question="Agent cache?",
        kalshi_title="Agent cache?",
        poly_title="Agent cache?",
        kalshi_yes_ask=0.42,
        poly_no_ask=0.48,
        gross_spread=0.08,
        net_edge=0.05,
        settlement_match_score=0.85,
        settlement_flags=[],
        volume_kalshi=20000,
        volume_poly=20000,
        category="macro",
        kelly_fraction=0.1,
    )
    store.save_arb_opportunities([opp])
    router = VenueRoutingBroker(
        equity_broker=PaperBrokerSimulator(cfg),
        polymarket_paper=PaperPolymarketBroker(cfg),
        kalshi_paper=PaperKalshiBroker(cfg),
        settings=cfg,
    )
    execution = ExecutionService(
        broker=router,
        risk_engine=RiskCheckEngine(cfg),
        store=store,
        settings=cfg,
    )
    engine = SimpleNamespace(settings=cfg, store=store, execution=execution)

    async def fake_submit(opp, thesis=None):
        return "K-PAPER", "P-PAPER"

    execution.submit_arb_paper_orders = fake_submit  # type: ignore[method-assign]
    monkeypatch.setattr("apex.services.arb_scan.scan_and_persist", lambda *a, **k: [])

    out = await run_kalshi_arb_agent_cycle(engine)  # type: ignore[arg-type]
    assert out.get("cached_used") is True
    assert out["scan_count"] >= 1


def test_pm_agents_status_execution_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = _settings(tmp_path, monkeypatch)
    store = SQLiteStore(cfg.sqlite_path)
    router = VenueRoutingBroker(
        equity_broker=PaperBrokerSimulator(cfg),
        polymarket_paper=PaperPolymarketBroker(cfg),
        kalshi_paper=PaperKalshiBroker(cfg),
        settings=cfg,
    )
    execution = ExecutionService(
        broker=router,
        risk_engine=RiskCheckEngine(cfg),
        store=store,
        settings=cfg,
    )
    engine = SimpleNamespace(settings=cfg, store=store, execution=execution)
    st = pm_agents_status(engine)  # type: ignore[arg-type]
    assert st["execution_mode"] == "paper_simulated"


def test_build_engine_has_pm_brokers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "audit.db"))
    monkeypatch.setenv("ALPACA_PAPER_TRADE", "true")
    monkeypatch.setenv("POLYMARKET_PAPER_TRADING_ENABLED", "true")
    engine = build_engine()
    broker = engine.execution.broker
    assert getattr(broker, "kalshi_paper", None) is not None
    assert getattr(broker, "polymarket_paper", None) is not None


def test_run_polymarket_agent_cycle_returns_error_on_discovery_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = _settings(tmp_path, monkeypatch)
    cfg = cfg.model_copy(update={"polymarket_automated_events_enabled": True})
    engine = SimpleNamespace(settings=cfg)
    engine.polymarket_event_discovery = lambda: (_ for _ in ()).throw(RuntimeError("boom"))  # type: ignore[attr-defined]
    engine.polymarket_paper_order_submission = lambda proposals: []  # type: ignore[attr-defined]

    out = run_polymarket_agent_cycle(engine)  # type: ignore[arg-type]
    assert out["status"] == "error"
    assert out["detail"].startswith("discovery_failed:")


def test_run_polymarket_agent_cycle_returns_error_on_submission_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = _settings(tmp_path, monkeypatch)
    cfg = cfg.model_copy(update={"polymarket_automated_events_enabled": True})
    engine = SimpleNamespace(settings=cfg)
    engine.polymarket_event_discovery = lambda: [{"id": "mkt"}]  # type: ignore[attr-defined]
    engine.polymarket_paper_order_submission = lambda proposals: (_ for _ in ()).throw(RuntimeError("submit"))  # type: ignore[attr-defined]

    out = run_polymarket_agent_cycle(engine)  # type: ignore[arg-type]
    assert out["status"] == "error"
    assert out["discovery_count"] == 1
    assert out["detail"].startswith("submission_failed:")
