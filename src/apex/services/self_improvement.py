"""Full self-improvement loop: export → train → evaluate → promote → feedback."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from apex.core.config import Settings, get_settings
from apex.core.logging import get_logger
from apex.domain.enums import EventType
from apex.domain.models import AuditEvent
from apex.ml.arb_edge_model import (
    ArbEdgeModel,
    evaluate_model,
    load_active_model,
    promote_model,
    train_from_rows,
    _model_dir,
)
from apex.repositories.sqlite_store import SQLiteStore
from apex.services.backtest_engine import BacktestEngine
from apex.services.training_export import collect_training_rows, export_training_corpus

LOGGER = get_logger(__name__)


def backfill_resolved_arb_labels(store: SQLiteStore | None = None) -> int:
    """Sync outcome/pnl from resolved arbs into export-ready state (no-op count audit)."""
    settings = get_settings()
    store = store or SQLiteStore(settings.sqlite_path)
    resolved = store.get_resolved_arb_opportunities(limit=500)
    return len(resolved)


def ml_status(store: SQLiteStore | None = None) -> dict[str, Any]:
    settings = get_settings()
    store = store or SQLiteStore(settings.sqlite_path)
    active = load_active_model(settings)
    rows = collect_training_rows(store)
    labeled = [r for r in rows if r.get("label_win") is not None]

    backtest = None
    try:
        bt = BacktestEngine(settings=settings, store=store).run(lookback_days=90)
        backtest = {
            "n_trades": bt.n_trades,
            "win_rate": bt.win_rate,
            "sharpe": bt.sharpe,
            "total_pnl": bt.total_pnl,
        }
    except Exception as exc:
        backtest = {"error": str(exc)}

    return {
        "self_improvement_enabled": settings.self_improvement_enabled,
        "active_model": active.to_dict() if active else None,
        "training_corpus": {
            "total_rows": len(rows),
            "labeled_rows": len(labeled),
            "resolved_arb_count": backfill_resolved_arb_labels(store),
        },
        "backtest_90d": backtest,
        "model_dir": str(_model_dir(settings)),
    }


def run_train_candidate(
    store: SQLiteStore | None = None,
    *,
    min_labeled: int | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    store = store or SQLiteStore(settings.sqlite_path)
    min_labeled = min_labeled or settings.self_improvement_min_labeled_samples

    export_summary = export_training_corpus(store=store)
    rows = collect_training_rows(store)
    labeled = [r for r in rows if r.get("label_win") is not None]

    if len(labeled) < min_labeled:
        return {
            "status": "insufficient_data",
            "detail": f"need {min_labeled} labeled rows, have {len(labeled)}",
            "export": export_summary,
        }

    model = train_from_rows(labeled)
    if model is None:
        return {"status": "error", "detail": "training failed"}

    model_dir = _model_dir(settings) / f"candidate_{model.version}"
    model_dir.mkdir(parents=True, exist_ok=True)
    model_path = model_dir / "model.json"
    model_path.write_text(json.dumps(model.to_dict(), indent=2), encoding="utf-8")

    eval_metrics = evaluate_model(model, labeled)
    active = load_active_model(settings)
    if active:
        eval_metrics["active_accuracy"] = evaluate_model(active, labeled).get("accuracy", 0)

    return {
        "status": "ok",
        "model_path": str(model_path),
        "export": export_summary,
        "train_metrics": model.metrics,
        "eval_metrics": eval_metrics,
    }


def run_evaluate_promote(
    store: SQLiteStore | None = None,
    *,
    candidate_path: Path | None = None,
    force: bool = False,
) -> dict[str, Any]:
    settings = get_settings()
    store = store or SQLiteStore(settings.sqlite_path)

    if candidate_path is None:
        cand_dir = _model_dir(settings)
        candidates = sorted(cand_dir.glob("candidate_*/model.json"), reverse=True)
        if not candidates:
            return {"status": "error", "detail": "no candidate model; run train first"}
        candidate_path = candidates[0]

    candidate = ArbEdgeModel.from_dict(
        json.loads(candidate_path.read_text(encoding="utf-8"))
    )
    rows = collect_training_rows(store)
    labeled = [r for r in rows if r.get("label_win") is not None]
    cand_eval = evaluate_model(candidate, labeled)
    active = load_active_model(settings)
    active_eval = evaluate_model(active, labeled) if active else {"accuracy": 0.0}

    min_gain = settings.self_improvement_min_accuracy_gain
    cand_acc = float(cand_eval.get("accuracy", 0))
    active_acc = float(active_eval.get("accuracy", 0))
    enough = cand_eval.get("n_samples", 0) >= settings.self_improvement_min_labeled_samples
    if force:
        promote_ok = enough
    elif active is None:
        promote_ok = enough
    else:
        promote_ok = enough and cand_acc >= active_acc + min_gain

    if not promote_ok:
        return {
            "status": "rejected",
            "candidate_metrics": cand_eval,
            "active_metrics": active_eval,
            "detail": "candidate did not beat active model accuracy threshold",
        }

    promote_model(candidate_path, cand_eval, settings)
    store.append_event(
        AuditEvent(
            event_type=EventType.SYSTEM_ALERT,
            raw_payload={
                "phase": "self_improvement_promote",
                "model_version": candidate.version,
                "candidate_metrics": cand_eval,
                "previous_active": active.version if active else None,
            },
        )
    )
    return {
        "status": "promoted",
        "model_path": str(candidate_path),
        "candidate_metrics": cand_eval,
        "active_metrics": active_eval,
    }


def run_self_improvement_cycle(engine: Any | None = None) -> dict[str, Any]:
    """Full loop: export, train, evaluate/promote, refresh brain feedback."""
    settings = get_settings()
    if not settings.self_improvement_enabled:
        return {"status": "disabled", "detail": "SELF_IMPROVEMENT_ENABLED=false"}

    store = SQLiteStore(settings.sqlite_path)
    train_out = run_train_candidate(store)
    if train_out.get("status") != "ok":
        return {"status": train_out.get("status", "skipped"), "train": train_out}

    candidate_path = Path(train_out["model_path"])
    promote_out = run_evaluate_promote(store, candidate_path=candidate_path)

    feedback: dict[str, Any] = {}
    if engine is not None:
        try:
            engine.brain_context_refresh()
            feedback = engine.observability.feedback_threshold_adjustments()
        except Exception as exc:
            feedback = {"error": str(exc)}

    store.append_event(
        AuditEvent(
            event_type=EventType.SYSTEM_ALERT,
            raw_payload={
                "phase": "self_improvement_cycle",
                "train": train_out,
                "promote": promote_out,
                "feedback": feedback,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
    )

    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "train": train_out,
        "promote": promote_out,
        "feedback": feedback,
    }
