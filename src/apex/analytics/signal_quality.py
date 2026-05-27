"""APEX Signal Quality Tracker - Track signal accuracy over time (uses consolidated audit.db)"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class SignalQualityTracker:
    """Track and analyze signal quality by source, conviction level, etc."""
    
    def __init__(self, db_path: str | Path = "data/audit.db"):
        from apex.repositories.sqlite_store import SQLiteStore
        self.store = SQLiteStore(Path(db_path))
    
    def record_signal(self, signal: dict[str, Any]) -> bool:
        """Record a new signal for tracking."""
        return self.store.record_signal(signal)
    
    def close_signal(self, signal_id: str, exit_price: float, pnl: float = 0, pnl_pct: float = 0) -> bool:
        """Mark a signal as closed with P&L."""
        return self.store.close_signal(signal_id, exit_price, pnl, pnl_pct)
    
    def get_source_stats(self) -> dict[str, dict]:
        """Get performance stats by signal source."""
        return self.store.get_source_stats()
    
    def get_conviction_accuracy(self) -> list[dict]:
        """Get win rate by conviction level."""
        return self.store.get_conviction_accuracy()


_singleton: SignalQualityTracker | None = None

def get_signal_tracker() -> SignalQualityTracker:
    global _singleton
    if _singleton is None:
        _singleton = SignalQualityTracker()
    return _singleton
