"""Export audit, arb, and signal data for ML self-improvement."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from apex.core.config import get_settings
from apex.repositories.sqlite_store import SQLiteStore


def _arb_feature_row(opp: dict[str, Any], *, source: str = "arb_opportunity") -> dict[str, Any]:
    pnl = float(opp.get("pnl") or 0)
    outcome = opp.get("outcome")
    if outcome is not None and str(outcome).lower() in ("win", "won", "yes"):
        label = 1
    elif outcome is not None and str(outcome).lower() in ("loss", "lost", "no"):
        label = 0
    elif pnl > 0:
        label = 1
    elif pnl < 0:
        label = 0
    else:
        label = None
    flags = opp.get("settlement_flags")
    if isinstance(flags, str):
        try:
            flags = json.loads(flags)
        except json.JSONDecodeError:
            flags = []
    return {
        "source": source,
        "id": opp.get("id"),
        "kalshi_ticker": opp.get("kalshi_ticker"),
        "net_edge": float(opp.get("net_edge") or 0),
        "gross_spread": float(opp.get("gross_spread") or 0),
        "settlement_match_score": float(opp.get("settlement_match_score") or 0),
        "volume_kalshi": float(opp.get("volume_kalshi") or 0),
        "volume_poly": float(opp.get("volume_poly") or 0),
        "kalshi_yes_ask": float(opp.get("kalshi_yes_ask") or 0),
        "poly_no_ask": float(opp.get("poly_no_ask") or 0),
        "kelly_fraction": float(opp.get("kelly_fraction") or 0),
        "settlement_flag_count": len(flags or []),
        "label_win": label,
        "pnl": pnl,
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }


def collect_training_rows(store: SQLiteStore | None = None) -> list[dict[str, Any]]:
    """Build labeled + unlabeled rows from SQLite."""
    settings = get_settings()
    store = store or SQLiteStore(settings.sqlite_path)
    rows: list[dict[str, Any]] = []

    for opp in store.list_arb_opportunities(limit=2000):
        rows.append(_arb_feature_row(opp))

    try:
        for wc in store.list_world_cup_opportunities(limit=500):
            me = float(wc.get("model_edge") or 0)
            label = 1 if me > 0.05 else (0 if me < -0.05 else None)
            rows.append(
                {
                    "source": "world_cup",
                    "id": wc.get("id"),
                    "kalshi_ticker": wc.get("kalshi_ticker") or "",
                    "net_edge": float(wc.get("net_edge") or 0),
                    "gross_spread": 0.0,
                    "settlement_match_score": 0.75,
                    "volume_kalshi": float(wc.get("volume_24h") or 0),
                    "volume_poly": float(wc.get("volume_24h") or 0),
                    "kalshi_yes_ask": float(wc.get("market_yes_ask") or 0.5),
                    "poly_no_ask": 0.5,
                    "kelly_fraction": 0.0,
                    "settlement_flag_count": 0,
                    "label_win": label,
                    "model_edge": me,
                    "contract_type": wc.get("contract_type"),
                    "exported_at": datetime.now(timezone.utc).isoformat(),
                }
            )
    except Exception:
        pass

    try:
        for raw in store.read_table("audit_log", limit=2000):
            et = str(raw.get("event_type") or "")
            if et not in ("ARB_PAPER_SUBMITTED", "ORDER_FILLED"):
                continue
            payload = raw.get("raw_payload")
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except json.JSONDecodeError:
                    payload = {}
            if not isinstance(payload, dict):
                continue
            if payload.get("arb_id") or payload.get("kalshi_ticker"):
                rows.append(
                    {
                        "source": "audit",
                        "id": payload.get("arb_id") or raw.get("order_id"),
                        "kalshi_ticker": payload.get("kalshi_ticker") or raw.get("symbol"),
                        "net_edge": float(payload.get("net_edge") or 0),
                        "gross_spread": float(payload.get("gross_spread") or 0),
                        "settlement_match_score": float(
                            payload.get("settlement_match_score") or 0
                        ),
                        "volume_kalshi": 0.0,
                        "volume_poly": 0.0,
                        "kalshi_yes_ask": float(payload.get("kalshi_yes_ask") or payload.get("entry_price") or 0),
                        "poly_no_ask": float(payload.get("poly_no_ask") or 0),
                        "kelly_fraction": 0.0,
                        "settlement_flag_count": 0,
                        "label_win": None,
                        "pnl": float(raw.get("pl_realized") or 0),
                        "exported_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
    except Exception:
        pass

    try:
        from apex.integrations.polymarket_gamma_public import (
            fetch_closed_markets_for_training,
            training_row_from_market,
        )

        for m in fetch_closed_markets_for_training(limit=50):
            tr = training_row_from_market(m)
            yes_won = tr.get("yes_won")
            rows.append(
                {
                    "source": "polymarket_gamma",
                    "id": tr.get("market_id"),
                    "kalshi_ticker": "",
                    "net_edge": float(tr.get("yes_implied_at_snapshot") or 0) * 0.1,
                    "gross_spread": 0.05,
                    "settlement_match_score": 0.8,
                    "volume_kalshi": 0.0,
                    "volume_poly": float(tr.get("volume") or 0),
                    "kalshi_yes_ask": float(tr.get("yes_implied_at_snapshot") or 0.5),
                    "poly_no_ask": 0.5,
                    "kelly_fraction": 0.0,
                    "settlement_flag_count": 0,
                    "label_win": 1 if yes_won is True else (0 if yes_won is False else None),
                    "pnl": None,
                    "exported_at": datetime.now(timezone.utc).isoformat(),
                }
            )
    except Exception:
        pass

    return rows


def export_training_corpus(
    path: Path | None = None,
    store: SQLiteStore | None = None,
) -> dict[str, Any]:
    """Write JSONL training corpus; returns summary stats."""
    settings = get_settings()
    path = path or (settings.sqlite_path.parent / "training" / "corpus.jsonl")
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)

    rows = collect_training_rows(store)
    labeled = [r for r in rows if r.get("label_win") is not None]

    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, default=str) + "\n")

    return {
        "path": str(path),
        "total_rows": len(rows),
        "labeled_rows": len(labeled),
        "positive_rate": (
            sum(1 for r in labeled if r["label_win"] == 1) / len(labeled) if labeled else 0.0
        ),
    }
