"""Tests for bulk showcase demo seeding."""

from __future__ import annotations

from apex.demo.bulk_seed import generate_bulk_arb_opportunities, generate_demo_proposal_events
from apex.demo.seed_data import seed_showcase_database
from apex.repositories.sqlite_store import SQLiteStore


def test_generate_bulk_arb_opportunities_count_and_ordering():
    rows = generate_bulk_arb_opportunities(100)
    assert len(rows) == 100
    assert rows[0].net_edge >= rows[-1].net_edge
    assert all(r.id.startswith("demo-arb-") for r in rows)


def test_generate_demo_proposal_events():
    events = generate_demo_proposal_events(32)
    assert len(events) == 32
    assert all(str(e.event_type) == "PROPOSAL_CREATED" or e.event_type.value == "PROPOSAL_CREATED" for e in events)


def test_seed_showcase_database_idempotent(tmp_path, monkeypatch):
    db = tmp_path / "showcase.db"
    monkeypatch.setenv("SHOWCASE_MODE", "true")
    monkeypatch.setenv("SHOWCASE_ARB_COUNT", "100")
    monkeypatch.setenv("SHOWCASE_PROPOSAL_COUNT", "32")
    monkeypatch.setenv("SQLITE_PATH", str(db))
    from apex.core.config import get_settings

    get_settings.cache_clear()
    store = SQLiteStore(str(db))
    stats1 = seed_showcase_database(store)
    stats2 = seed_showcase_database(store)
    assert stats1["opportunities"] == 100
    assert stats2["opportunities"] == 100
    listed = store.list_arb_opportunities(limit=200)
    assert len(listed) == 100
