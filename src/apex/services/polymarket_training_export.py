"""Append public resolved Polymarket (Gamma) rows as JSONL for offline training."""

from __future__ import annotations

import json
from pathlib import Path

from apex.integrations.polymarket_gamma_public import (
    fetch_closed_markets_for_training,
    training_row_from_market,
)


def export_resolved_markets_to_jsonl(
    path: Path,
    *,
    limit: int = 200,
    offset: int = 0,
) -> int:
    """
    Fetch closed markets from Gamma and append one JSON object per line.

    Labels use ``yes_won`` when terminal ``outcomePrices`` clearly resolve YES/NO.
    """
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = fetch_closed_markets_for_training(limit=limit, offset=offset)
    n = 0
    with path.open("a", encoding="utf-8") as f:
        for m in rows:
            rec = training_row_from_market(m)
            f.write(json.dumps(rec, default=str) + "\n")
            n += 1
    return n
