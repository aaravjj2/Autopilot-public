"""Normalize SQLite arb_opportunities rows for API and WebSocket consumers."""

from __future__ import annotations

import json
from typing import Any


def normalize_arb_row(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    sf = out.get("settlement_flags", "[]")
    if isinstance(sf, str):
        try:
            out["settlement_flags"] = json.loads(sf) if sf else []
        except json.JSONDecodeError:
            out["settlement_flags"] = []
    elif sf is None:
        out["settlement_flags"] = []
    else:
        out["settlement_flags"] = list(sf)

    if out.get("detected_at") and not out.get("detection_ts"):
        out["detection_ts"] = out["detected_at"]

    out["net_edge"] = float(out.get("net_edge") or 0)
    out["gross_spread"] = float(out.get("gross_spread") or 0)
    out["kalshi_yes_ask"] = float(out.get("kalshi_yes_ask") or 0)
    out["poly_no_ask"] = float(out.get("poly_no_ask") or 0)
    out["settlement_match_score"] = float(out.get("settlement_match_score") or 0)
    out["volume_kalshi"] = float(out.get("volume_kalshi") or 0)
    out["volume_poly"] = float(out.get("volume_poly") or 0)
    out["kelly_fraction"] = float(out.get("kelly_fraction") or 0)
    out["vwap_edge"] = float(out.get("vwap_edge") or 0)
    return out


def normalize_arb_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [normalize_arb_row(r) for r in rows]
