from __future__ import annotations

from datetime import datetime, timezone, timedelta
from pathlib import Path

from apex.domain.enums import Direction
from apex.domain.models import Position
from apex.services.exit_monitor import evaluate_position_exit

from test_integrations_and_autotrade import _engine, _opportunity


def _settings_exit(tmp_path: Path, **overrides):
    from apex.core.config import Settings

    payload = {
        "SQLITE_PATH": tmp_path / "audit.db",
        "CHROMADB_PATH": tmp_path / "chromadb",
        "EXIT_MONITOR_ENABLED": True,
        "EXIT_MAX_HOLD_DAYS": 3,
        "EXIT_EOD_FLATTEN_ENABLED": True,
        "EXIT_SIGNAL_REVERSAL_ENABLED": True,
        "EXIT_USE_PROPOSAL_STOPS": True,
        "EXIT_STOP_PCT": 4.0,
        "EXIT_TAKE_PROFIT_PCT": 10.0,
        "CONVICTION_FLOOR": 6.0,
    }
    payload.update(overrides)
    return Settings(**payload)


def test_eod_flatten_closes_position(tmp_path: Path) -> None:
    engine = _engine(tmp_path, autotrade_all_approved=False)
    broker = engine.execution.broker
    broker.positions["AAPL"] = Position(
        symbol="AAPL",
        qty=10.0,
        market_value=1000.0,
        sector="Technology",
        avg_entry_price=100.0,
        side="long",
    )
    engine.eod_flatten_all_positions()
    assert "AAPL" not in broker.positions


def test_max_hold_days_triggers_exit(tmp_path: Path) -> None:
    settings = _settings_exit(tmp_path)
    pos = Position(
        symbol="MSFT",
        qty=1.0,
        market_value=100.0,
        sector="Technology",
        avg_entry_price=100.0,
        side="long",
        entry_time=datetime.now(tz=timezone.utc) - timedelta(days=5),
    )
    decision = evaluate_position_exit(
        position=pos,
        price=101.0,
        settings=settings,
        opportunity=None,
        entry_time=pos.entry_time,
        proposal_targets=None,
        eod_flatten=False,
    )
    assert decision is not None
    assert decision.reason == "max_hold_days"


def test_signal_reversal_on_long_when_bearish_score(tmp_path: Path) -> None:
    settings = _settings_exit(tmp_path)
    pos = Position(
        symbol="NVDA",
        qty=1.0,
        market_value=100.0,
        sector="Technology",
        avg_entry_price=100.0,
        side="long",
    )
    opp = _opportunity("NVDA")
    opp.direction = Direction.SHORT
    opp.conviction = 7.0
    decision = evaluate_position_exit(
        position=pos,
        price=100.0,
        settings=settings,
        opportunity=opp,
        entry_time=datetime.now(tz=timezone.utc),
        proposal_targets=None,
        eod_flatten=False,
    )
    assert decision is not None
    assert decision.reason == "signal_reversal"


def test_proposal_stop_loss_for_long(tmp_path: Path) -> None:
    settings = _settings_exit(tmp_path)
    pos = Position(
        symbol="AAPL",
        qty=1.0,
        market_value=90.0,
        sector="Technology",
        avg_entry_price=100.0,
        side="long",
    )
    decision = evaluate_position_exit(
        position=pos,
        price=95.0,
        settings=settings,
        opportunity=None,
        entry_time=datetime.now(tz=timezone.utc),
        proposal_targets={"stop_loss": 96.0, "take_profit": 110.0},
        eod_flatten=False,
    )
    assert decision is not None
    assert decision.reason == "proposal_stop_loss"
