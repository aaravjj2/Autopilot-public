"""Decision/outcome logging and calibration metrics."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from db.schema import init_db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_decision(decision: dict, context: dict, db_conn) -> int:
    init_db(db_conn)
    cur = db_conn.execute(
        """
        INSERT INTO decisions (
            decided_at, platform, market_id, question, market_implied_prob,
            agent_estimated_prob, edge, action, recommended_stake,
            kelly_fraction, reasoning, context_snapshot
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            _now(),
            context.get("platform"),
            context.get("market_id"),
            context.get("question"),
            decision.get("market_implied_prob"),
            decision.get("agent_estimated_prob"),
            decision.get("edge"),
            decision.get("action"),
            decision.get("stake"),
            decision.get("kelly_fraction"),
            decision.get("reasoning", ""),
            json.dumps(context, default=str),
        ),
    )
    db_conn.commit()
    return int(cur.lastrowid)


def log_outcome(decision_id: int, outcome: str, db_conn):
    d = db_conn.execute("SELECT * FROM decisions WHERE id=?", (decision_id,)).fetchone()
    if not d:
        raise ValueError("decision not found")
    action = d["action"]
    implied = float(d["market_implied_prob"] or 0.5)
    stake = float(d["recommended_stake"] or 0)
    yes_win = action == "bet_yes" and outcome == "yes"
    no_win = action == "bet_no" and outcome == "no"
    was_correct = bool(yes_win or no_win)
    # Binary contract approximation payout
    pnl = stake * ((1 - implied) / implied) if was_correct and implied > 0 else -stake
    db_conn.execute(
        """
        INSERT INTO outcomes (decision_id, resolved_at, outcome, profit_loss, was_correct)
        VALUES (?, ?, ?, ?, ?)
        """,
        (decision_id, _now(), outcome, pnl, 1 if was_correct else 0),
    )
    db_conn.commit()


def get_calibration_stats(db_conn) -> dict:
    if db_conn is None:
        from db.queries import get_conn

        db_conn = get_conn()
    init_db(db_conn)
    rows = db_conn.execute(
        """
        SELECT d.id, d.action, d.edge, d.recommended_stake, o.was_correct, o.profit_loss,
               json_extract(d.context_snapshot, '$.closes_at') AS closes_at,
               json_extract(d.context_snapshot, '$.question') AS question
        FROM decisions d
        LEFT JOIN outcomes o ON o.decision_id = d.id
        WHERE d.action IN ('bet_yes', 'bet_no')
        """
    ).fetchall()
    total = len(rows)
    if total == 0:
        return {
            "total_bets": 0,
            "correct_bets": 0,
            "accuracy": 0.0,
            "avg_edge": 0.0,
            "roi": 0.0,
            "by_stage": {"group": {"accuracy": 0.0, "roi": 0.0}, "knockout": {"accuracy": 0.0, "roi": 0.0}},
        }
    correct = sum(int(r["was_correct"] or 0) for r in rows)
    avg_edge = sum(float(r["edge"] or 0) for r in rows) / total
    stake_sum = sum(float(r["recommended_stake"] or 0) for r in rows) or 1.0
    pnl = sum(float(r["profit_loss"] or 0) for r in rows)
    roi = pnl / stake_sum
    return {
        "total_bets": total,
        "correct_bets": correct,
        "accuracy": correct / total,
        "avg_edge": avg_edge,
        "roi": roi,
        "by_stage": {"group": {"accuracy": correct / total, "roi": roi}, "knockout": {"accuracy": correct / total, "roi": roi}},
    }


def get_brier_score(db_conn) -> float:
    rows = db_conn.execute(
        """
        SELECT d.agent_estimated_prob, o.outcome
        FROM decisions d
        JOIN outcomes o ON o.decision_id = d.id
        WHERE d.action IN ('bet_yes', 'bet_no')
        """
    ).fetchall()
    if not rows:
        return 0.25
    err = 0.0
    for r in rows:
        p = float(r["agent_estimated_prob"] or 0.5)
        y = 1.0 if str(r["outcome"]).lower() == "yes" else 0.0
        err += (p - y) ** 2
    return err / len(rows)
