from calibration.tracker import get_brier_score, get_calibration_stats, log_decision, log_outcome
from config import get_db_connection
from db.schema import init_db


def _ctx():
    return {
        "platform": "kalshi",
        "market_id": "X",
        "question": "Q",
        "implied_prob": 0.5,
        "closes_at": "2026-01-01T00:00:00Z",
    }


def _decision(action="bet_yes", p=0.7):
    return {
        "action": action,
        "stake": 10,
        "kelly_fraction": 0.01,
        "edge": 0.2,
        "agent_estimated_prob": p,
        "market_implied_prob": 0.5,
        "reasoning": "r",
        "key_factors": ["a"],
        "red_flags": [],
    }


def test_log_decision_inserts_row():
    conn = get_db_connection()
    init_db(conn)
    before = conn.execute("SELECT COUNT(*) c FROM decisions").fetchone()[0]
    log_decision(_decision(), _ctx(), conn)
    after = conn.execute("SELECT COUNT(*) c FROM decisions").fetchone()[0]
    assert after == before + 1


def test_log_outcome_updates_correctly():
    conn = get_db_connection()
    init_db(conn)
    did = log_decision(_decision("bet_yes", 0.8), _ctx(), conn)
    log_outcome(did, "yes", conn)
    row = conn.execute("SELECT was_correct FROM outcomes WHERE decision_id=?", (did,)).fetchone()
    assert row[0] == 1


def test_calibration_stats_empty_db():
    conn = get_db_connection()
    init_db(conn)
    conn.execute("DELETE FROM decisions")
    conn.execute("DELETE FROM outcomes")
    conn.commit()
    s = get_calibration_stats(conn)
    assert s["total_bets"] == 0


def test_brier_score_perfect():
    conn = get_db_connection()
    init_db(conn)
    conn.execute("DELETE FROM decisions")
    conn.execute("DELETE FROM outcomes")
    conn.commit()
    did = log_decision(_decision("bet_yes", 1.0), _ctx(), conn)
    log_outcome(did, "yes", conn)
    assert get_brier_score(conn) == 0.0


def test_brier_score_random():
    conn = get_db_connection()
    init_db(conn)
    conn.execute("DELETE FROM decisions")
    conn.execute("DELETE FROM outcomes")
    conn.commit()
    did1 = log_decision(_decision("bet_yes", 0.5), _ctx(), conn)
    did2 = log_decision(_decision("bet_no", 0.5), _ctx(), conn)
    log_outcome(did1, "yes", conn)
    log_outcome(did2, "no", conn)
    score = get_brier_score(conn)
    assert 0.24 <= score <= 0.26
