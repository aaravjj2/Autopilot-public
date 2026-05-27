"""Self-improvement export, train, evaluate, promote."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from apex.domain.models import ArbOpportunity
from apex.ml.arb_edge_model import (
    apply_model_scores,
    evaluate_model,
    load_active_model,
    train_from_rows,
)
from apex.services.self_improvement import (
    ml_status,
    run_evaluate_promote,
    run_train_candidate,
)
from apex.services.training_export import collect_training_rows, export_training_corpus


def _labeled_rows(n: int = 8) -> list[dict]:
    rows = []
    for i in range(n):
        win = i % 2 == 0
        rows.append(
            {
                "net_edge": 0.05 if win else 0.01,
                "gross_spread": 0.08,
                "settlement_match_score": 0.85,
                "volume_kalshi": 1000.0 * (i + 1),
                "volume_poly": 800.0 * (i + 1),
                "kalshi_yes_ask": 0.42,
                "poly_no_ask": 0.48,
                "kelly_fraction": 0.1,
                "settlement_flag_count": 0,
                "label_win": 1 if win else 0,
            }
        )
    return rows


def _arb_opportunities_from_rows(rows: list[dict]) -> list[ArbOpportunity]:
    opps = []
    for i, row in enumerate(rows):
        opps.append(
            ArbOpportunity(
                id=f"arb-{i}",
                kalshi_ticker=f"KX{i}",
                poly_market_id=f"0x{i}",
                question=f"Q{i}",
                kalshi_title=f"Q{i}",
                poly_title=f"Q{i}",
                kalshi_yes_ask=row["kalshi_yes_ask"],
                poly_no_ask=row["poly_no_ask"],
                gross_spread=row["gross_spread"],
                net_edge=row["net_edge"],
                settlement_match_score=row["settlement_match_score"],
                settlement_flags=[],
                volume_kalshi=row["volume_kalshi"],
                volume_poly=row["volume_poly"],
                category="macro",
                kelly_fraction=row["kelly_fraction"],
                detection_ts=datetime.now(timezone.utc),
                outcome="WIN" if row["label_win"] else "LOSS",
                pnl=5.0 if row["label_win"] else -3.0,
            )
        )
    return opps


def test_train_evaluate_promote(tmp_path, monkeypatch):
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "audit.db"))
    from apex.core.config import get_settings
    from apex.repositories.sqlite_store import SQLiteStore

    settings = get_settings()
    store = SQLiteStore(settings.sqlite_path)
    rows = _labeled_rows(10)
    store.save_arb_opportunities(_arb_opportunities_from_rows(rows))

    export = export_training_corpus(store=store)
    assert export["labeled_rows"] >= 5

    train_out = run_train_candidate(store, min_labeled=5)
    assert train_out["status"] == "ok"
    model_path = Path(train_out["model_path"])
    assert model_path.is_file()

    promote_out = run_evaluate_promote(store, candidate_path=model_path, force=True)
    assert promote_out["status"] == "promoted"
    assert load_active_model(settings) is not None

    scored = apply_model_scores(collect_training_rows(store)[:3])
    assert "model_score" in scored[0]

    st = ml_status(store)
    assert st["active_model"] is not None


def test_train_from_rows_minimum():
    model = train_from_rows(_labeled_rows(5))
    assert model is not None
    ev = evaluate_model(model, _labeled_rows(5))
    assert ev["n_samples"] == 5
