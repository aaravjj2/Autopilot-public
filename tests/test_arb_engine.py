from __future__ import annotations

import pytest
from pathlib import Path
from types import SimpleNamespace

from apex.repositories.sqlite_store import SQLiteStore


@pytest.mark.smoke
def test_topics_compatible_blocks_cross_topic_false_positives() -> None:
    from apex.services.arb_engine import _topics_compatible

    assert _topics_compatible("Will X happen?", "Will X happen?") is True
    assert not _topics_compatible(
        "NYC temperature above 85 degrees",
        "Will Bitcoin be above $72,000 on May 26?",
    )


def test_scan_and_persist_demo(tmp_path: Path, monkeypatch) -> None:
    # Create a small in-memory sqlite via temp file
    db_path = tmp_path / "test_arb.db"
    store = SQLiteStore(db_path)

    # Stub Kalshi client
    fake_kal = SimpleNamespace()
    fake_kal.get_macro_markets = lambda min_volume=0, fast=True: [
        SimpleNamespace(ticker="KAL_1", title="Will X happen?", volume_24h=20000, best_ask_yes=0.40)
    ]

    # Stub Polymarket fetch
    fake_pm = [
        {"id": "pm1", "question": "Will X happen?", "volume24hr": 20000, "bestAsk_no": 0.45}
    ]

    from apex.services.arb_engine import ArbEngine
    from apex.core.config import Settings

    settings = Settings(alpaca_paper_trade=True)
    engine = ArbEngine(settings=settings, store=store)

    import apex.services.arb_engine as arb_engine_mod
    monkeypatch.setattr(arb_engine_mod, "KalshiEventClient", lambda s: fake_kal)

    # Mock Polymarket local import by patching the function inside arb_engine
    monkeypatch.setattr(arb_engine_mod, "fetch_active_liquid_markets", lambda **kwargs: fake_pm, raising=False)

    # Mock ChromaMarketStore
    fake_chroma = SimpleNamespace()
    fake_chroma.upsert_market = lambda id, title, plat: None
    fake_chroma.find_semantic_match = lambda title, plat, top_k=5: [("pm1", 0.9)]
    import apex.integrations.chromadb_market_store as chroma_mod
    monkeypatch.setattr(chroma_mod, "ChromaMarketStore", lambda path: fake_chroma)

    # Mock SettlementAuditor
    fake_auditor = SimpleNamespace()
    fake_auditor.verify = lambda k, p, **kwargs: SimpleNamespace(match_score=0.9, flags=[])
    import apex.services.settlement_auditor as auditor_mod
    monkeypatch.setattr(auditor_mod, "SettlementAuditor", lambda **kwargs: fake_auditor)

    # Mock Polymarket fetch locally inside the function (since it's imported locally)
    # Actually it's easier to mock it in sys.modules or just patch the arb_engine module since Python binds it there if it's imported at the top,
    # but it's imported LOCALLY inside scan(). So we must patch it at the source.
    import apex.integrations.polymarket_gamma_public as poly_gamma
    monkeypatch.setattr(poly_gamma, "fetch_active_liquid_markets", lambda **kwargs: fake_pm)

    found = engine.scan()
    assert isinstance(found, list)
    assert len(found) > 0

    # Simulate persist
    store.save_arb_opportunities(found)
    rows = store.list_arb_opportunities()
    assert len(rows) == len(found)


def test_scan_returns_empty_when_polymarket_circuit_open(tmp_path: Path) -> None:
    from apex.core.config import Settings
    from apex.services.arb_engine import ArbEngine

    db_path = tmp_path / "test_arb_circuit.db"
    store = SQLiteStore(db_path)
    engine = ArbEngine(settings=Settings(alpaca_paper_trade=True), store=store)
    engine._poly_errors = engine.CIRCUIT_THRESHOLD
    engine._poly_last_error = 10**12  # force cooldown-not-elapsed path

    assert engine.scan() == []


def test_scan_deduplicates_kalshi_poly_pairs(tmp_path: Path, monkeypatch) -> None:
    from apex.core.config import Settings
    from apex.services.arb_engine import ArbEngine
    import apex.services.arb_engine as arb_engine_mod
    import apex.integrations.chromadb_market_store as chroma_mod
    import apex.integrations.polymarket_gamma_public as poly_gamma
    import apex.services.settlement_auditor as auditor_mod

    store = SQLiteStore(tmp_path / "dedupe.db")
    settings = Settings(alpaca_paper_trade=True, arb_min_net_edge=0.01)
    engine = ArbEngine(settings=settings, store=store)

    fake_kal = SimpleNamespace()
    fake_kal.get_macro_markets = lambda **_kwargs: [
        SimpleNamespace(ticker="KX-1", title="Will X happen?", volume_24h=20000, best_ask_yes=0.40)
    ]
    fake_pm = [
        {"id": "pm1", "question": "Will X happen?", "volume24hr": 20000, "bestAsk_no": 0.45},
    ]
    fake_chroma = SimpleNamespace(
        upsert_market=lambda *_args, **_kwargs: None,
        find_semantic_match=lambda *_args, **_kwargs: [("pm1", 0.9)],
    )
    fake_auditor = SimpleNamespace(verify=lambda *_args, **_kwargs: SimpleNamespace(match_score=0.9, flags=[]))

    monkeypatch.setattr(arb_engine_mod, "KalshiEventClient", lambda _s: fake_kal)
    monkeypatch.setattr(poly_gamma, "fetch_active_liquid_markets", lambda **_kwargs: fake_pm)
    monkeypatch.setattr(chroma_mod, "ChromaMarketStore", lambda _path: fake_chroma)
    monkeypatch.setattr(auditor_mod, "SettlementAuditor", lambda **_kwargs: fake_auditor)
    monkeypatch.setattr(engine, "_combined_match", lambda *_args, **_kwargs: fake_pm[0])

    out = engine.scan()
    assert len(out) == 1
