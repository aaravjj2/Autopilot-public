"""In-process latency observability for the arb scan hot path.

Lightweight, dependency-free counters/gauges that record how long the most
recent scans took (fetch vs. match vs. total), how effective the coalesce guard
is (hit-rate), and rolling averages. Surfaced via the ``/api/arb/metrics``
endpoint and useful for the latency regression benchmark.
"""

from __future__ import annotations

import threading
from collections import deque
from typing import Any

_LOCK = threading.Lock()
_MAX_SAMPLES = 50

_state: dict[str, Any] = {
    "scans": 0,
    "coalesce_hits": 0,
    "coalesce_misses": 0,
    "last": {},
    "scan_ms": deque(maxlen=_MAX_SAMPLES),
    "fetch_ms": deque(maxlen=_MAX_SAMPLES),
    "match_ms": deque(maxlen=_MAX_SAMPLES),
}


def record_coalesce_hit() -> None:
    with _LOCK:
        _state["coalesce_hits"] += 1


def record_scan(
    *,
    total_ms: float,
    fetch_ms: float,
    match_ms: float,
    kalshi_count: int,
    poly_count: int,
    opportunities: int,
) -> None:
    """Record one completed (non-coalesced) scan."""
    with _LOCK:
        _state["scans"] += 1
        _state["coalesce_misses"] += 1
        _state["scan_ms"].append(round(total_ms, 1))
        _state["fetch_ms"].append(round(fetch_ms, 1))
        _state["match_ms"].append(round(match_ms, 1))
        _state["last"] = {
            "total_ms": round(total_ms, 1),
            "fetch_ms": round(fetch_ms, 1),
            "match_ms": round(match_ms, 1),
            "kalshi_count": kalshi_count,
            "poly_count": poly_count,
            "opportunities": opportunities,
        }


def _avg(samples: deque) -> float:
    return round(sum(samples) / len(samples), 1) if samples else 0.0


def snapshot() -> dict[str, Any]:
    """Return a JSON-serializable view of current scan metrics."""
    with _LOCK:
        triggers = _state["coalesce_hits"] + _state["coalesce_misses"]
        hit_rate = (_state["coalesce_hits"] / triggers) if triggers else 0.0
        return {
            "scans_completed": _state["scans"],
            "coalesce_hits": _state["coalesce_hits"],
            "coalesce_misses": _state["coalesce_misses"],
            "coalesce_hit_rate": round(hit_rate, 3),
            "avg_scan_ms": _avg(_state["scan_ms"]),
            "avg_fetch_ms": _avg(_state["fetch_ms"]),
            "avg_match_ms": _avg(_state["match_ms"]),
            "last_scan": dict(_state["last"]),
        }


def reset() -> None:
    """Clear all recorded metrics (used by tests/benchmarks)."""
    with _LOCK:
        _state["scans"] = 0
        _state["coalesce_hits"] = 0
        _state["coalesce_misses"] = 0
        _state["last"] = {}
        _state["scan_ms"].clear()
        _state["fetch_ms"].clear()
        _state["match_ms"].clear()
