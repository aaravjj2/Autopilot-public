"""PM brain cache and fast path (Phase 1)."""

from __future__ import annotations

from apex.core.config import Settings
from apex.repositories.sqlite_store import SQLiteStore
from apex.services import pm_brain
from apex.services.fast_cache import invalidate


def test_pm_brain_uses_cache(tmp_path):
    store = SQLiteStore(tmp_path / "audit.db")
    settings = Settings(SQLITE_PATH=tmp_path / "audit.db", ALPACA_PAPER_TRADE=True)
    invalidate(f"pm_brain:{settings.sqlite_path}")

    calls = {"n": 0}
    original = pm_brain._build_pm_brain_uncached

    def counting_build(s, st):
        calls["n"] += 1
        return original(s, st)

    pm_brain._build_pm_brain_uncached = counting_build  # type: ignore[method-assign]
    try:
        pm_brain.build_pm_brain(store, force=True)
        pm_brain.build_pm_brain(store)
        pm_brain.build_pm_brain(store)
        assert calls["n"] == 1
    finally:
        pm_brain._build_pm_brain_uncached = original  # type: ignore[method-assign]


def test_pm_brain_structure(tmp_path):
    store = SQLiteStore(tmp_path / "audit.db")
    out = pm_brain.build_pm_brain(store, force=True)
    assert "kalshi" in out
    assert "polymarket" in out
    assert "arb" in out
    assert out["paper_only"] is True
