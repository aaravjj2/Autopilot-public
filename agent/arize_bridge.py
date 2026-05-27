from __future__ import annotations

import os
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Iterator

from apex.core.logging import get_logger

LOGGER = get_logger(__name__)


@dataclass
class ArizeSpan:
    trace_id: str
    span_id: str
    name: str
    attributes: dict[str, Any] = field(default_factory=dict)
    status: str = "OK"


class ArizeBridge:
    """Lightweight trace recorder for Arize MCP / OTLP export in hackathon demos."""

    def __init__(self) -> None:
        self._enabled = os.getenv("ARIZE_ENABLED", "true").lower() in ("1", "true", "yes")
        self._project = os.getenv("ARIZE_PROJECT_NAME", "apex-finops-agent")
        self._spans: list[ArizeSpan] = []

    @contextmanager
    def span(
        self,
        name: str,
        *,
        trace_id: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> Iterator[ArizeSpan]:
        tid = trace_id or uuid.uuid4().hex
        sid = uuid.uuid4().hex[:16]
        rec = ArizeSpan(trace_id=tid, span_id=sid, name=name, attributes=dict(attributes or {}))
        if self._enabled:
            self._spans.append(rec)
            LOGGER.info(
                "arize span project=%s trace=%s name=%s attrs=%s",
                self._project,
                tid[:12],
                name,
                list((attributes or {}).keys()),
            )
        try:
            yield rec
        except Exception as exc:
            rec.status = "ERROR"
            rec.attributes["error"] = str(exc)
            raise
        finally:
            if self._enabled:
                rec.attributes.setdefault("status", rec.status)

    def recent_spans(self, limit: int = 50) -> list[dict[str, Any]]:
        return [
            {
                "trace_id": s.trace_id,
                "span_id": s.span_id,
                "name": s.name,
                "status": s.status,
                "attributes": s.attributes,
                "project": self._project,
            }
            for s in self._spans[-limit:]
        ]

    def trace_url(self, trace_id: str) -> str:
        base = os.getenv("ARIZE_UI_BASE", "https://app.arize.com")
        return f"{base}/traces/{self._project}/{trace_id}"


_bridge: ArizeBridge | None = None


def get_arize_bridge() -> ArizeBridge:
    global _bridge
    if _bridge is None:
        _bridge = ArizeBridge()
    return _bridge
