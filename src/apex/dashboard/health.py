from __future__ import annotations

import os
from dataclasses import dataclass

from apex.core.config import Settings


@dataclass
class ProbeRow:
    status: str
    detail: str = ""


def _probe_llm_route(settings: Settings) -> ProbeRow:
    """Lightweight probe used by tests: warn if GROQ provider is selected but key missing."""
    provider = getattr(settings, "llm_provider", "")
    if provider.lower() == "groq":
        if not os.getenv("GROQ_API_KEY"):
            return ProbeRow(status="warn", detail="GROQ_API_KEY missing from environment")
    return ProbeRow(status="ok", detail="")
