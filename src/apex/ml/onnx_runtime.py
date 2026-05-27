"""ONNX runtime loader (Phase 5 backlog — optional model path)."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger(__name__)


def load_onnx_session(model_path: str | Path | None = None) -> Any | None:
    path = Path(model_path or os.getenv("APEX_ONNX_MODEL_PATH", "data/models/spread_collapse.onnx"))
    if not path.is_file():
        LOGGER.debug("ONNX model not found at %s — using heuristic fallback", path)
        return None
    try:
        import onnxruntime as ort

        return ort.InferenceSession(str(path))
    except Exception as exc:
        LOGGER.warning("ONNX load failed: %s", exc)
        return None


def predict_with_session(session: Any, features: list[float]) -> float | None:
    if session is None:
        return None
    try:
        import numpy as np

        inp = np.array([features], dtype=np.float32)
        name = session.get_inputs()[0].name
        out = session.run(None, {name: inp})[0]
        return float(out[0][0])
    except Exception as exc:
        LOGGER.warning("ONNX predict failed: %s", exc)
        return None
