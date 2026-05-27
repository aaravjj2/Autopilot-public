from __future__ import annotations

from apex.domain.watchlist_candidates import DEFAULT_WATCHLIST_CANDIDATES


def test_default_watchlist_includes_user_blue_chips_and_etfs() -> None:
    assert "NVDA" in DEFAULT_WATCHLIST_CANDIDATES
    assert "SMH" in DEFAULT_WATCHLIST_CANDIDATES
    assert "SOXX" in DEFAULT_WATCHLIST_CANDIDATES
    assert "AAPL" in DEFAULT_WATCHLIST_CANDIDATES
    assert "JPM" in DEFAULT_WATCHLIST_CANDIDATES
    assert "GLD" in DEFAULT_WATCHLIST_CANDIDATES
    assert "SLV" in DEFAULT_WATCHLIST_CANDIDATES
    assert "BRK-B" in DEFAULT_WATCHLIST_CANDIDATES
    assert "TSLA" not in DEFAULT_WATCHLIST_CANDIDATES
    assert len(DEFAULT_WATCHLIST_CANDIDATES) >= 50
    assert len(DEFAULT_WATCHLIST_CANDIDATES) == len(set(DEFAULT_WATCHLIST_CANDIDATES))
