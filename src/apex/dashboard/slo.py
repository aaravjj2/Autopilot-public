from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


ET = timezone.utc


@dataclass
class SloRow:
    job_name: str
    stale: bool


def build_pipeline_slo_rows(jobs: list[dict], now: datetime) -> list[SloRow]:
    """Simple SLO row builder for tests: failed -> stale, success -> not stale."""
    rows: list[SloRow] = []
    for j in jobs:
        name = j.get("job_name")
        status = j.get("status")
        # Simplified logic: only success is not stale.
        stale = status != "success"
        rows.append(SloRow(job_name=name, stale=stale))
    return rows
