"""CFTC persistence: flush, hydrate, restart-survival."""
from __future__ import annotations

import pytest

from apex.risk.cftc_limits import CftcLimitTracker


def test_flush_and_hydrate_roundtrip(tmp_path):
    """Notional written by flush is readable by hydrate on the same day."""
    from apex.repositories.cftc_persistence import flush_exposure, hydrate_tracker
    from apex.repositories.sqlite_store import SQLiteStore

    store = SQLiteStore(tmp_path / "test.db")
    flush_exposure(store, "KX-CPI-25", 75_000.0)
    flush_exposure(store, "KX-FED-25", 50_000.0)

    result = hydrate_tracker(store)
    assert result["KX-CPI-25"] == pytest.approx(75_000.0)
    assert result["KX-FED-25"] == pytest.approx(50_000.0)


def test_flush_upserts_on_same_ticker(tmp_path):
    """Subsequent flush for same ticker updates, does not duplicate."""
    from apex.repositories.cftc_persistence import flush_exposure, hydrate_tracker
    from apex.repositories.sqlite_store import SQLiteStore

    store = SQLiteStore(tmp_path / "test.db")
    flush_exposure(store, "KX-CPI-25", 50_000.0)
    flush_exposure(store, "KX-CPI-25", 120_000.0)

    result = hydrate_tracker(store)
    assert len([k for k in result if k == "KX-CPI-25"]) == 1
    assert result["KX-CPI-25"] == pytest.approx(120_000.0)


def test_hydrate_returns_empty_dict_on_fresh_db(tmp_path):
    """hydrate_tracker on a new DB returns {} without crashing."""
    from apex.repositories.cftc_persistence import hydrate_tracker
    from apex.repositories.sqlite_store import SQLiteStore

    store = SQLiteStore(tmp_path / "fresh.db")
    result = hydrate_tracker(store)
    assert result == {}


def test_tracker_hydrated_on_restart_survives_m09(tmp_path):
    """After hydration, M09 correctly sees pre-restart exposure."""
    from apex.repositories.cftc_persistence import flush_exposure, hydrate_tracker
    from apex.repositories.sqlite_store import SQLiteStore

    store = SQLiteStore(tmp_path / "test.db")
    flush_exposure(store, "KX-MACRO-25", 240_000.0)

    fresh_tracker = CftcLimitTracker(limit_usd=250_000.0)
    exposures = hydrate_tracker(store)
    for ticker, notional in exposures.items():
        fresh_tracker.set_exposure(ticker, notional)

    result = fresh_tracker.check("KX-MACRO-25", 20_000.0)
    assert result.breached, "Should breach: $240k existing + $20k new > $250k"
