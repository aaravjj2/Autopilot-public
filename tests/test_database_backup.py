"""Tests for SQLite connection lifecycle in backup operations.

Verifies the `with sqlite3.connect()` context manager pattern correctly
closes connections and does not emit ResourceWarnings.
"""
from __future__ import annotations

import sqlite3
import warnings
from pathlib import Path

import pytest


# The pattern used in engine.py's database_backup() after the fix:
#   with sqlite3.connect(src) as src_conn, sqlite3.connect(dst) as dst_conn:
#       src_conn.backup(dst_conn)
# This test validates the pattern at the connection level.


def _backup_pattern(src: Path, dst: Path) -> None:
    """Exact connection pattern used by engine.py's database_backup()."""
    with (
        sqlite3.connect(str(src)) as src_conn,
        sqlite3.connect(str(dst)) as dst_conn,
    ):
        src_conn.backup(dst_conn)


def test_backup_pattern_has_no_leaks(tmp_path: Path) -> None:
    """Backup with context manager must not leak connections."""
    src = tmp_path / "source.db"
    dst = tmp_path / "backup.db"

    conn = sqlite3.connect(str(src))
    conn.execute("CREATE TABLE t (id INTEGER)")
    conn.execute("INSERT INTO t VALUES (1)")
    conn.commit()
    conn.close()

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        _backup_pattern(src, dst)
        resource_warnings = [x for x in w if issubclass(x.category, ResourceWarning)]

    assert len(resource_warnings) == 0, (
        f"ResourceWarning(s) detected: {[str(x.message) for x in resource_warnings]}"
    )

    # Verify backup is valid
    verify = sqlite3.connect(str(dst))
    row = verify.execute("SELECT id FROM t").fetchone()
    assert row is not None
    assert row[0] == 1
    verify.close()


def test_context_manager_closes_on_exception(tmp_path: Path) -> None:
    """If backup fails mid-way, context manager must still close connections."""
    src = tmp_path / "source.db"
    dst = tmp_path / "nonexistent" / "backup.db"  # parent doesn't exist

    conn = sqlite3.connect(str(src))
    conn.execute("CREATE TABLE t (id INTEGER)")
    conn.close()

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        # This should fail because dst parent doesn't exist
        with pytest.raises(Exception):
            with (
                sqlite3.connect(str(src)) as src_conn,
                sqlite3.connect(str(dst)) as dst_conn,
            ):
                src_conn.backup(dst_conn)

        resource_warnings = [x for x in w if issubclass(x.category, ResourceWarning)]

    # Even on failure, no connections should leak
    assert len(resource_warnings) == 0, (
        f"ResourceWarning(s) on failure: {[str(x.message) for x in resource_warnings]}"
    )


def test_health_server_pattern_no_leaks(tmp_path: Path) -> None:
    """The health_server.py pattern (with sqlite3.connect as conn) must not leak."""
    src = tmp_path / "health.db"

    # Create db with expected table
    conn = sqlite3.connect(str(src))
    conn.execute("CREATE TABLE completed_trades (id INTEGER, pnl REAL, exit_time TEXT)")
    conn.execute(
        "INSERT INTO completed_trades VALUES (1, 100.0, date('now'))"
    )
    conn.commit()
    conn.close()

    # Exact pattern from health_server.py after the fix
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        with sqlite3.connect(str(src)) as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*), COALESCE(SUM(pnl),0) FROM completed_trades "
                "WHERE exit_time >= date('now')"
            )
            row = cur.fetchone()
            assert row is not None
            assert row[0] == 1

        resource_warnings = [x for x in w if issubclass(x.category, ResourceWarning)]

    assert len(resource_warnings) == 0, (
        f"ResourceWarning(s): {[str(x.message) for x in resource_warnings]}"
    )
