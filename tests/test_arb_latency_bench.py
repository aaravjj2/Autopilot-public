"""Latency benchmark + regression guards for the arb scan hot path.

These tests assert that the wave-2 performance work stays correct and fast:

* the inverted-index prefilter selects the *same* best match as a brute-force
  scan over the full Polymarket book (no precision regression), and
* the coalesce guard reports hits and populates latency metrics.

The wall-clock budget is intentionally generous so the test is a coarse
regression tripwire (catching e.g. an accidental O(K*P*expensive) blow-up)
rather than a flaky microbenchmark.
"""

from __future__ import annotations

import time
from pathlib import Path
from types import SimpleNamespace

from apex.core.config import Settings
from apex.repositories.sqlite_store import SQLiteStore
from apex.services.arb_engine import ArbEngine, _tokens


def _synthetic_poly_book(n: int) -> list[dict]:
    book = [
        {
            "id": f"pm{i}",
            "question": f"Will candidate number {i} win the special election in district {i}?",
            "volume24hr": 20000,
            "bestAsk_no": 0.45,
        }
        for i in range(n)
    ]
    # Inject one market that clearly matches the Kalshi title below.
    book.append(
        {
            "id": "pm_match",
            "question": "Will the Fed raise rates at the next FOMC meeting?",
            "volume24hr": 50000,
            "bestAsk_no": 0.45,
        }
    )
    return book


def _make_engine(tmp_path: Path) -> ArbEngine:
    store = SQLiteStore(tmp_path / "bench.db")
    settings = Settings(alpaca_paper_trade=True, arb_min_net_edge=0.01)
    return ArbEngine(settings=settings, store=store)


def test_prefilter_matches_bruteforce(tmp_path: Path) -> None:
    """The inverted-index candidate set must yield the same best match as a
    brute-force scan over the entire book."""
    engine = _make_engine(tmp_path)
    poly = _synthetic_poly_book(600)
    kalshi_title = "Will the Fed raise rates at the next FOMC meeting?"

    chroma = SimpleNamespace(find_semantic_match=lambda *_a, **_k: [])

    # Brute force (poly_index=None) and prefiltered must agree.
    poly_index: dict[str, list[int]] = {}
    for idx, p in enumerate(poly):
        for tok in _tokens(p.get("question", "")):
            poly_index.setdefault(tok, []).append(idx)

    brute = engine._combined_match(kalshi_title, poly, chroma, None)
    fast = engine._combined_match(kalshi_title, poly, chroma, poly_index)

    assert brute is not None
    assert fast is not None
    assert fast["id"] == brute["id"] == "pm_match"


def test_prefilter_latency_budget(tmp_path: Path) -> None:
    """Matching a Kalshi title against a large book stays well under budget."""
    engine = _make_engine(tmp_path)
    poly = _synthetic_poly_book(1000)
    chroma = SimpleNamespace(find_semantic_match=lambda *_a, **_k: [])

    poly_index: dict[str, list[int]] = {}
    for idx, p in enumerate(poly):
        for tok in _tokens(p.get("question", "")):
            poly_index.setdefault(tok, []).append(idx)

    t0 = time.perf_counter()
    for _ in range(50):
        engine._combined_match(
            "Will the Fed raise rates at the next FOMC meeting?",
            poly,
            chroma,
            poly_index,
        )
    elapsed = time.perf_counter() - t0
    # 50 matches against a 1000-market book; generous tripwire.
    assert elapsed < 5.0, f"matching too slow: {elapsed:.2f}s"


def test_coalesce_records_metrics(tmp_path: Path, monkeypatch) -> None:
    """A second scan within the coalesce window is a hit and reuses the result;
    metrics reflect one completed scan and one coalesce hit."""
    import apex.integrations.chromadb_market_store as chroma_mod
    import apex.integrations.polymarket_gamma_public as poly_gamma
    import apex.services.arb_engine as arb_engine_mod
    import apex.services.arb_scan as arb_scan_mod
    import apex.services.settlement_auditor as auditor_mod
    from apex.observability import scan_metrics

    settings = Settings(alpaca_paper_trade=True, arb_min_net_edge=0.01)
    store = SQLiteStore(tmp_path / "coalesce.db")

    fake_kal = SimpleNamespace(
        get_macro_markets=lambda **_k: [
            SimpleNamespace(
                ticker="KX-FED",
                title="Will the Fed raise rates at the next FOMC meeting?",
                volume_24h=20000,
                best_ask_yes=0.40,
            )
        ]
    )
    fake_pm = [
        {
            "id": "pm_match",
            "question": "Will the Fed raise rates at the next FOMC meeting?",
            "volume24hr": 50000,
            "bestAsk_no": 0.45,
        }
    ]
    fake_chroma = SimpleNamespace(
        upsert_market=lambda *_a, **_k: None,
        find_semantic_match=lambda *_a, **_k: [("pm_match", 0.9)],
    )
    fake_auditor = SimpleNamespace(
        verify=lambda *_a, **_k: SimpleNamespace(match_score=0.9, flags=[])
    )

    monkeypatch.setattr(arb_engine_mod, "KalshiEventClient", lambda _s: fake_kal)
    monkeypatch.setattr(poly_gamma, "fetch_active_liquid_markets", lambda **_k: fake_pm)
    monkeypatch.setattr(chroma_mod, "ChromaMarketStore", lambda _p: fake_chroma)
    monkeypatch.setattr(auditor_mod, "SettlementAuditor", lambda **_k: fake_auditor)
    # Ensure a non-zero coalesce window regardless of environment.
    monkeypatch.setattr(arb_scan_mod, "_SCAN_COALESCE_SEC", 25.0)
    arb_scan_mod._SCAN_STATE.clear()
    scan_metrics.reset()

    first = arb_scan_mod.scan_and_persist(store, settings=settings, limit=50, ingest_l2=False)
    second = arb_scan_mod.scan_and_persist(store, settings=settings, limit=50, ingest_l2=False)

    assert len(first) == 1
    assert len(second) == 1

    snap = scan_metrics.snapshot()
    assert snap["scans_completed"] == 1
    assert snap["coalesce_hits"] == 1
    assert snap["coalesce_hit_rate"] == 0.5
    assert snap["last_scan"]["opportunities"] == 1
