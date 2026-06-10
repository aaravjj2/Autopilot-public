from __future__ import annotations

import pytest
from pathlib import Path

from apex.integrations.chromadb_market_store import ChromaMarketStore

# Skip entire test when chromadb (optional heavy dep) is not installed –
# mirrors the graceful ImportError fallback in ChromaMarketStore.__init__.
chromadb = pytest.importorskip("chromadb", reason="chromadb not installed")


def test_chromadb_upsert_and_find(tmp_path: Path) -> None:
    store = ChromaMarketStore(chromadb_path=tmp_path / "chromadb")

    # Wait, the prompt mentions `settings.chromadb_path`
    # We should just test the class
    store.upsert_market("poly_1", "Will Bitcoin reach $100k?", "polymarket")
    store.upsert_market("kalshi_1", "Bitcoin hits $100,000", "kalshi")
    store.upsert_market("kalshi_2", "Ethereum to 10k", "kalshi")

    # We are searching for kalshi match given polymarket title, or vice-versa
    # The existing find_semantic_match automatically searches the OTHER platform
    # find_semantic_match(title="Will Bitcoin reach $100k?", platform="polymarket")
    # -> it will search for platform: kalshi
    matches = store.find_semantic_match("Will Bitcoin reach $100k?", "polymarket", top_k=2)

    assert len(matches) > 0
    match_id, score = matches[0]
    assert match_id == "kalshi_1"
    assert score > 0.5
