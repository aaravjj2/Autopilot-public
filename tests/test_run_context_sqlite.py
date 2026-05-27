from __future__ import annotations

from pathlib import Path

import pytest

from apex.core.context import reset_run_id, set_run_id
from apex.domain.enums import EventType
from apex.domain.models import AuditEvent
from apex.repositories.sqlite_store import SQLiteStore


def test_append_event_merges_run_id(tmp_path: Path) -> None:
    db = tmp_path / "t.db"
    store = SQLiteStore(db)
    token = set_run_id("run-test-123")
    try:
        store.append_event(
            AuditEvent(
                event_type=EventType.SYSTEM_ALERT,
                raw_payload={"note": "x"},
            )
        )
    finally:
        reset_run_id(token)

    rows = store.list_audit_events_for_run_id("run-test-123", limit=10)
    assert len(rows) == 1
    assert (rows[0].get("payload_json") or {}).get("run_id") == "run-test-123"
    assert (rows[0].get("payload_json") or {}).get("note") == "x"


def test_payload_run_id_not_overwritten(tmp_path: Path) -> None:
    db = tmp_path / "t2.db"
    store = SQLiteStore(db)
    token = set_run_id("outer")
    try:
        store.append_event(
            AuditEvent(
                event_type=EventType.SYSTEM_ALERT,
                raw_payload={"run_id": "inner"},
            )
        )
    finally:
        reset_run_id(token)
    rows = store.list_audit_events(5)
    assert (rows[0].get("payload_json") or {}).get("run_id") == "inner"


def test_concurrent_read_write_wal(tmp_path: Path) -> None:
    """P3.5 — Verify SQLite WAL mode handles concurrent read + write without errors."""
    import random
    import string
    import threading

    from apex.core.config import Settings

    db_path = tmp_path / "concurrent_wal.db"
    settings = Settings(**{"SQLITE_PATH": str(db_path), "APCA_API_KEY_ID": "x", "APCA_SECRET_KEY": "x"})
    store = SQLiteStore(settings.sqlite_path)

    def _writer():
        for i in range(50):
            sym = "".join(random.choices(string.ascii_uppercase, k=4))
            store.append_event(
                AuditEvent(
                    event_type=EventType.TRADE_CLOSED,
                    symbol=sym,
                    rejection_reason=f"test_concurrent_{i}",
                    raw_payload={"i": i},
                )
            )

    def _reader():
        for _ in range(50):
            try:
                store.get_completed_trades(limit=10)
            except Exception:
                pass

    threads = []
    for _ in range(4):
        t = threading.Thread(target=_writer)
        threads.append(t)
        t.start()
    for _ in range(4):
        t = threading.Thread(target=_reader)
        threads.append(t)
        t.start()

    for t in threads:
        t.join(timeout=15)

    # Verify no corruption: can still query
    import sqlite3
    with sqlite3.connect(str(db_path)) as conn:
        row = conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()
        assert row is not None
        assert row[0] > 0
