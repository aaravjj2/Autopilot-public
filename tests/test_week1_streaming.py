"""Week 1: Redis L2, JSON Patch, mmap Kalshi ticks."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from apex.cache.orderbook_l2 import ingest_orderbook, read_orderbook
from apex.cache.redis_client import reset_redis_for_tests
from apex.ingestion.kalshi_tick_mmap import KalshiTickMmapReader
from apex.streaming.arb_patch_diff import apply_patch_document, diff_opportunities


@pytest.fixture(autouse=True)
def _reset_redis():
    reset_redis_for_tests()
    yield
    reset_redis_for_tests()


def test_l2_orderbook_ingest_memory_fallback():
    book = {"yes": [[0.45, 100], [0.44, 200]], "no": [[0.55, 50]]}
    ingest_orderbook("KALSHI", "KX-TEST", book, redis_url="")
    out = read_orderbook("KALSHI", "KX-TEST", redis_url="")
    assert out["yes"][0] == [0.45, 100.0]
    assert out["no"][0] == [0.55, 50.0]


def test_json_patch_diff_replace_and_add():
    prev = [{"id": "a", "net_edge": 0.04}]
    curr = [
        {"id": "a", "net_edge": 0.05},
        {"id": "b", "net_edge": 0.03, "kalshi_ticker": "KX-B"},
    ]
    patches = diff_opportunities(prev, curr)
    doc = apply_patch_document({"opportunities": prev}, patches)
    assert len(doc["opportunities"]) == 2
    assert doc["opportunities"][0]["net_edge"] == 0.05


def test_json_patch_diff_remove():
    prev = [
        {"id": "a", "net_edge": 0.04},
        {"id": "b", "net_edge": 0.03},
    ]
    curr = [{"id": "a", "net_edge": 0.04}]
    patches = diff_opportunities(prev, curr)
    doc = apply_patch_document({"opportunities": prev}, patches)
    assert len(doc["opportunities"]) == 1
    assert doc["opportunities"][0]["id"] == "a"


def test_kalshi_tick_mmap_roundtrip():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "ticks.jsonl"
        KalshiTickMmapReader.append_tick(path, {"ticker": "KX-1", "price": 0.5})
        KalshiTickMmapReader.append_tick(path, {"ticker": "KX-2", "price": 0.6})
        with KalshiTickMmapReader(path) as reader:
            ticks = list(reader.iter_ticks())
        assert len(ticks) == 2
        assert ticks[0].ticker == "KX-1"
        assert ticks[1].payload["price"] == 0.6


def test_arb_patch_stream_sync_then_patch():
    from apex.streaming.arb_patch_stream import ArbPatchStream

    stream = ArbPatchStream()
    rows = [{"id": "x", "net_edge": 0.1}]
    sync = stream.build_message(rows, force_full=True)
    assert sync["type"] == "sync"
    rows[0]["net_edge"] = 0.12
    patch = stream.build_message(rows)
    assert patch["type"] == "patch"
    assert any(p["op"] == "replace" for p in patch["patches"])
