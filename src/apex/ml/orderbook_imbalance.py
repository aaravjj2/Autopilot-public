"""Orderbook imbalance features for XGBoost (Week 4 stub)."""

from __future__ import annotations

from typing import Any


def imbalance_features(book: dict[str, Any]) -> dict[str, float]:
    yes = book.get("yes") or []
    no = book.get("no") or []
    bid_vol = sum(float(r[1]) for r in yes[:5] if isinstance(r, (list, tuple)))
    ask_vol = sum(float(r[1]) for r in no[:5] if isinstance(r, (list, tuple)))
    total = bid_vol + ask_vol + 1e-9
    return {
        "bid_ask_ratio": bid_vol / total,
        "imbalance": (bid_vol - ask_vol) / total,
        "depth_bid": bid_vol,
        "depth_ask": ask_vol,
    }


def predict_spread_collapse(features: dict[str, float]) -> float:
    """Heuristic with optional ONNX (Phase 5)."""
    from apex.ml.onnx_runtime import load_onnx_session, predict_with_session

    vec = [
        float(features.get("bid_ask_ratio", 1.0)),
        float(features.get("spread_velocity", 0.0)),
        float(features.get("depth_imbalance", 0.0)),
    ]
    session = load_onnx_session()
    onnx_score = predict_with_session(session, vec)
    if onnx_score is not None:
        return max(0.0, min(1.0, onnx_score))
    return min(0.99, max(0.0, 0.5 + features.get("imbalance", 0) * 0.3))
