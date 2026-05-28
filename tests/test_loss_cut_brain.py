from __future__ import annotations

from unittest.mock import MagicMock

from apex.layers.l3.loss_cut_brain import (
    _daily_loss_exceeded,
    _loss_threshold,
    _peak_pnl,
    _unrealized_pnl_pct,
    loss_cut_scan,
)


class FakePos:
    def __init__(self, symbol: str, side: str = "long", raw: dict | None = None):
        self.symbol = symbol
        self.side = side
        self._raw = raw or {}


class FakeAccount:
    def __init__(self, positions: list):
        self.open_positions = positions


def test_loss_threshold_equity_default() -> None:
    assert _loss_threshold({"asset_class": "us_equity"}, 1) == 4.0


def test_loss_threshold_option_default() -> None:
    assert _loss_threshold({"asset_class": "us_option"}, 1) == 30.0


def test_loss_threshold_decays_over_time() -> None:
    t0 = _loss_threshold({"asset_class": "us_equity"}, 1)
    t1 = _loss_threshold({"asset_class": "us_equity"}, 240)
    assert t0 > t1


def test_unrealized_pnl_pct_uses_plpc() -> None:
    assert _unrealized_pnl_pct({"unrealized_plpc": -0.05}) == -5.0


def test_unrealized_pnl_pct_zero_on_missing() -> None:
    assert _unrealized_pnl_pct({}) == 0.0


def test_peak_pnl_tracks_highest() -> None:
    assert _peak_pnl({"peak_pnl_pct": 5.0}, 3.0) == 5.0
    assert _peak_pnl({"peak_pnl_pct": 5.0}, 8.0) == 8.0
    assert _peak_pnl({}, 2.0) == 2.0


def test_daily_loss_exceeded_returns_false_when_within_limit() -> None:
    store = MagicMock()
    store.get_completed_trades.return_value = [{"pnl": -50.0}]
    settings = MagicMock()
    settings.daily_loss_limit_pct = 3.0
    settings.initial_account_equity = 100000.0
    assert not _daily_loss_exceeded(store, settings)


def test_loss_cut_scan_skips_positions_within_threshold() -> None:
    broker = MagicMock()
    broker.get_account_snapshot.return_value = FakeAccount([
        FakePos("AAPL", raw={"unrealized_plpc": -0.01, "asset_class": "us_equity"}),
    ])
    store = MagicMock()
    closed = loss_cut_scan(settings=MagicMock(), broker=broker, store=store, market_data=MagicMock())
    assert closed == []
    broker.close_symbol_position.assert_not_called()


def test_loss_cut_scan_closes_position_exceeding_threshold() -> None:
    broker = MagicMock()
    broker.get_account_snapshot.return_value = FakeAccount([
        FakePos("TSLA", raw={"unrealized_plpc": -0.08, "asset_class": "us_equity"}),
    ])
    broker.close_symbol_position.return_value = True
    store = MagicMock()
    closed = loss_cut_scan(settings=MagicMock(), broker=broker, store=store, market_data=MagicMock())
    assert closed == ["TSLA"]
    broker.close_symbol_position.assert_called_once_with("TSLA")


def test_exit_monitor_invalid_entry_triggers_exit() -> None:
    from apex.domain.models import Position
    from apex.services.exit_monitor import evaluate_position_exit
    from apex.core.config import Settings

    pos = Position(symbol="BAD", qty=0, market_value=0, sector="X", avg_entry_price=0, side="long", correlation_to_book=0, entry_time=__import__("datetime").datetime.now())
    decision = evaluate_position_exit(
        position=pos,
        price=100.0,
        settings=Settings(**{"EXIT_STOP_PCT": 4.0, "EXIT_TAKE_PROFIT_PCT": 10.0, "EXIT_MAX_HOLD_DAYS": 5, "EXIT_EOD_FLATTEN_ENABLED": True, "EXIT_SIGNAL_REVERSAL_ENABLED": True, "EXIT_USE_PROPOSAL_STOPS": True, "EXIT_MONITOR_ENABLED": True}),
        opportunity=None,
        entry_time=__import__("datetime").datetime.now(),
        proposal_targets=None,
        eod_flatten=False,
    )
    assert decision is not None
    assert decision.reason == "invalid_entry_price"


def test_health_endpoint_enriched() -> None:
    from starlette.testclient import TestClient
    from apex.monitor.health_server import app

    client = TestClient(app)
    resp = client.get("/healthz?deep=1")
    assert resp.status_code in (200, 503)
    data = resp.json()
    assert "status" in data
