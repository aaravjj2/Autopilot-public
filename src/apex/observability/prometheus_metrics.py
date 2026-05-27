"""Prometheus metrics (Week 9 Day 1)."""

from __future__ import annotations

try:
    from prometheus_client import Counter, Gauge, Histogram, generate_latest

    HAS_PROM = True
except ImportError:
    HAS_PROM = False
    generate_latest = None  # type: ignore

if HAS_PROM:
    APEX_REQUESTS = Counter("apex_http_requests_total", "HTTP requests", ["method", "endpoint"])
    APEX_ARB_EDGE = Gauge("apex_arb_max_edge", "Max arb net edge")
    APEX_SLIPPAGE = Histogram(
        "apex_slippage_bps", "Slippage by venue", ["venue"], buckets=(1, 5, 10, 25, 50, 100)
    )
    APEX_ML_ACCURACY = Gauge("apex_ml_prediction_accuracy", "ML prediction accuracy")
    APEX_POSITIONS = Gauge("apex_positions_open", "Open positions count")
else:
    APEX_REQUESTS = APEX_ARB_EDGE = APEX_SLIPPAGE = APEX_ML_ACCURACY = APEX_POSITIONS = None


def metrics_payload() -> bytes:
    if not HAS_PROM or generate_latest is None:
        return b"# prometheus_client not installed\n"
    return generate_latest()
