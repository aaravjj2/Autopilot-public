from __future__ import annotations

import os
from dataclasses import dataclass

from apex.core.config import Settings


@dataclass
class ProbeRow:
    status: str
    detail: str = ""


def _probe_llm_route(settings: Settings) -> ProbeRow:
    """Report LLM availability; heuristic mode is always acceptable."""
    from apex.brain.finance_brain import FinanceBrain

    brain = FinanceBrain(settings)
    if brain.is_live:
        return ProbeRow(status="ok", detail=f"LLM route: {brain.route_label}")
    return ProbeRow(status="ok", detail="heuristic/scripts mode (no live LLM)")
