"""Arb scan service (Phase 2)."""

from __future__ import annotations

from unittest.mock import MagicMock

from apex.core.config import Settings
from apex.repositories.sqlite_store import SQLiteStore
from apex.services import arb_scan


def test_scan_and_persist_empty_when_no_markets(tmp_path, monkeypatch):
    settings = Settings(SQLITE_PATH=tmp_path / "audit.db", ALPACA_PAPER_TRADE=True)
    store = SQLiteStore(settings.sqlite_path)
    mock_engine = MagicMock()
    mock_engine.scan.return_value = []
    monkeypatch.setattr("apex.services.arb_scan.ArbEngine", lambda **kw: mock_engine)
    out = arb_scan.scan_and_persist(store, settings=settings, ingest_l2=False)
    assert out == []
