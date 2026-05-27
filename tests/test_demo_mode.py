from __future__ import annotations

from pathlib import Path

from apex.core.config import Settings
from apex.domain.models import AuditEvent
from apex.demo.seed_data import (
    DEMO_ARBITRAGE_OPPORTUNITIES,
    DEMO_AUDIT_EVENTS,
    seed_demo_database,
)
from apex.repositories.sqlite_store import SQLiteStore
from apex.services.arb_engine import ArbEngine


def test_demo_mode_scan_returns_seeded_opportunities(tmp_path: Path) -> None:
    db = tmp_path / "demo.db"
    settings = Settings(
        sqlite_path=db,
        demo_mode=True,
        alpaca_paper_trade=True,
        _env_file=None,
    )
    store = SQLiteStore(db)
    seed_demo_database(store)
    engine = ArbEngine(settings=settings, store=store)
    opps = engine.scan()
    assert len(opps) >= 5
    assert all(o.net_edge > 0 for o in opps if o.id != "demo-reject-demo")


def test_demo_seed_writes_audit(tmp_path: Path) -> None:
    db = tmp_path / "demo2.db"
    store = SQLiteStore(db)
    stats = seed_demo_database(store)
    assert stats["audit_events"] >= 3
    events = store.list_audit_events(limit=10)
    assert any("DEMO" in str(e.get("raw_payload", "")) or e.get("event_type") for e in events)


def test_demo_seed_idempotent(tmp_path: Path) -> None:
    db = tmp_path / "demo3.db"
    store = SQLiteStore(db)
    seed_demo_database(store)
    n_after_first = len(store.list_audit_events(limit=100))
    seed_demo_database(store)
    n_after_second = len(store.list_audit_events(limit=100))
    assert n_after_second == n_after_first
    assert store.get_arb_opportunity("demo-fed-jun") is not None


def test_demo_seed_handles_duplicate_audit_event_ids(tmp_path: Path) -> None:
    db = tmp_path / "demo4.db"
    store = SQLiteStore(db)
    duplicate = DEMO_AUDIT_EVENTS[0]
    store.append_event(
        AuditEvent(
            event_id=duplicate.event_id,
            event_type=duplicate.event_type,
            symbol="OTHER",
            raw_payload={"demo_mode": False},
        )
    )

    stats = seed_demo_database(store)
    assert stats["opportunities"] >= len(DEMO_ARBITRAGE_OPPORTUNITIES)
    assert store.get_arb_opportunity("demo-fed-jun") is not None
