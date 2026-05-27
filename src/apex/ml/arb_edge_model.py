"""Logistic edge model: train, evaluate, promote, and score arb opportunities."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from apex.core.config import Settings, get_settings
from apex.core.logging import get_logger

LOGGER = get_logger(__name__)

FEATURE_NAMES = [
    "net_edge",
    "gross_spread",
    "settlement_match_score",
    "volume_kalshi",
    "volume_poly",
    "kalshi_yes_ask",
    "poly_no_ask",
    "kelly_fraction",
    "settlement_flag_count",
]


def _sigmoid(z: float) -> float:
    z = max(-20.0, min(20.0, z))
    return 1.0 / (1.0 + math.exp(-z))


@dataclass
class ArbEdgeModel:
    weights: list[float]
    bias: float
    feature_names: list[str]
    metrics: dict[str, Any]
    version: str
    trained_at: str

    def predict_proba(self, row: dict[str, Any]) -> float:
        vec = feature_vector(row, self.feature_names)
        z = self.bias + sum(w * x for w, x in zip(self.weights, vec, strict=True))
        return _sigmoid(z)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "trained_at": self.trained_at,
            "feature_names": self.feature_names,
            "weights": self.weights,
            "bias": self.bias,
            "metrics": self.metrics,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ArbEdgeModel:
        return cls(
            weights=[float(x) for x in data["weights"]],
            bias=float(data.get("bias", 0)),
            feature_names=list(data.get("feature_names") or FEATURE_NAMES),
            metrics=dict(data.get("metrics") or {}),
            version=str(data.get("version", "unknown")),
            trained_at=str(data.get("trained_at", "")),
        )


def feature_vector(row: dict[str, Any], names: list[str] | None = None) -> list[float]:
    names = names or FEATURE_NAMES
    out: list[float] = []
    for n in names:
        v = float(row.get(n) or 0)
        if n in ("volume_kalshi", "volume_poly"):
            v = math.log1p(max(0.0, v))
        out.append(v)
    return out


def _data_root(settings: Settings | None = None) -> Path:
    settings = settings or get_settings()
    return settings.sqlite_path.expanduser().resolve().parent


def _model_dir(settings: Settings | None = None) -> Path:
    return (_data_root(settings) / "models" / "arb_edge").resolve()


def _active_pointer_path(settings: Settings | None = None) -> Path:
    return _model_dir(settings) / "active.json"


def load_active_model(settings: Settings | None = None) -> ArbEdgeModel | None:
    ptr = _active_pointer_path(settings)
    if not ptr.is_file():
        return None
    try:
        meta = json.loads(ptr.read_text(encoding="utf-8"))
        model_path = Path(meta["model_path"])
        if not model_path.is_file():
            return None
        return ArbEdgeModel.from_dict(json.loads(model_path.read_text(encoding="utf-8")))
    except Exception as exc:
        LOGGER.warning("load_active_model failed: %s", exc)
        return None


def promote_model(model_path: Path, metrics: dict[str, Any], settings: Settings | None = None) -> Path:
    settings = settings or get_settings()
    ptr = _active_pointer_path(settings)
    ptr.parent.mkdir(parents=True, exist_ok=True)
    ptr.write_text(
        json.dumps(
            {
                "model_path": str(model_path.resolve()),
                "promoted_at": datetime.now(timezone.utc).isoformat(),
                "metrics": metrics,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return ptr


def train_from_rows(
    rows: list[dict[str, Any]],
    *,
    epochs: int = 400,
    learning_rate: float = 0.08,
) -> ArbEdgeModel | None:
    """Train logistic regression on labeled rows (numpy-only)."""
    labeled = [r for r in rows if r.get("label_win") is not None]
    if len(labeled) < 3:
        LOGGER.warning("train_from_rows: need >= 3 labeled rows, got %d", len(labeled))
        return None

    n_feat = len(FEATURE_NAMES)
    weights = [0.0] * n_feat
    bias = 0.0

    for _ in range(epochs):
        for row in labeled:
            y = float(row["label_win"])
            vec = feature_vector(row)
            z = bias + sum(w * x for w, x in zip(weights, vec, strict=True))
            pred = _sigmoid(z)
            err = pred - y
            for i in range(n_feat):
                weights[i] -= learning_rate * err * vec[i]
            bias -= learning_rate * err

    correct = 0
    for row in labeled:
        pred = _sigmoid(
            bias + sum(w * x for w, x in zip(weights, feature_vector(row), strict=True))
        )
        if (pred >= 0.5) == bool(row["label_win"]):
            correct += 1
    acc = correct / len(labeled)

    preds = [
        _sigmoid(bias + sum(w * x for w, x in zip(weights, feature_vector(r), strict=True)))
        for r in labeled
    ]
    mean_pred = sum(preds) / len(preds) if preds else 0.5

    version = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return ArbEdgeModel(
        weights=weights,
        bias=bias,
        feature_names=list(FEATURE_NAMES),
        metrics={
            "n_samples": len(labeled),
            "accuracy": round(acc, 4),
            "mean_pred": round(mean_pred, 4),
        },
        version=version,
        trained_at=datetime.now(timezone.utc).isoformat(),
    )


def evaluate_model(
    model: ArbEdgeModel,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    labeled = [r for r in rows if r.get("label_win") is not None]
    if not labeled:
        return {"n_samples": 0, "accuracy": 0.0, "win_rate_baseline": 0.0}

    correct = wins = 0
    for row in labeled:
        pred = model.predict_proba(row) >= 0.5
        actual = bool(row["label_win"])
        if pred == actual:
            correct += 1
        if actual:
            wins += 1
    return {
        "n_samples": len(labeled),
        "accuracy": round(correct / len(labeled), 4),
        "win_rate_baseline": round(wins / len(labeled), 4),
        "model_metrics": model.metrics,
    }


def score_opportunity(row: dict[str, Any], model: ArbEdgeModel | None = None) -> float:
    """Combined score for ranking: model P(win) blended with net_edge."""
    model = model or load_active_model()
    edge = float(row.get("net_edge") or 0)
    if model is None:
        return edge
    p = model.predict_proba(row)
    return 0.55 * p + 0.45 * edge


def apply_model_scores(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    model = load_active_model()
    out: list[dict[str, Any]] = []
    for row in rows:
        r = dict(row)
        r["model_win_prob"] = model.predict_proba(row) if model else None
        r["model_score"] = score_opportunity(row, model)
        out.append(r)
    return sorted(out, key=lambda r: -(float(r.get("model_score") or 0)))
