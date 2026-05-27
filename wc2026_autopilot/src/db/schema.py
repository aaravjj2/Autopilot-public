"""SQLite schema for WC2026 autopilot."""

from __future__ import annotations

import sqlite3

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS wc_matches (
    id INTEGER PRIMARY KEY,
    tournament_year INTEGER,
    stage TEXT,
    home_team TEXT,
    away_team TEXT,
    home_goals INTEGER,
    away_goals INTEGER,
    home_goals_extra INTEGER,
    away_goals_extra INTEGER,
    winner TEXT,
    date TEXT,
    venue TEXT
);

CREATE TABLE IF NOT EXISTS international_results (
    id INTEGER PRIMARY KEY,
    date TEXT,
    home_team TEXT,
    away_team TEXT,
    home_score INTEGER,
    away_score INTEGER,
    tournament TEXT,
    neutral BOOLEAN
);

CREATE TABLE IF NOT EXISTS fixtures_2026 (
    id INTEGER PRIMARY KEY,
    match_date TEXT,
    kickoff_utc TEXT,
    home_team TEXT,
    away_team TEXT,
    venue TEXT,
    city TEXT,
    stage TEXT,
    group_name TEXT
);

CREATE TABLE IF NOT EXISTS market_snapshots (
    id INTEGER PRIMARY KEY,
    captured_at TEXT,
    platform TEXT,
    market_id TEXT,
    question TEXT,
    implied_prob REAL,
    volume REAL,
    open_interest REAL,
    closes_at TEXT,
    home_team TEXT,
    away_team TEXT,
    UNIQUE(platform, market_id, captured_at)
);

CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY,
    decided_at TEXT,
    platform TEXT,
    market_id TEXT,
    question TEXT,
    market_implied_prob REAL,
    agent_estimated_prob REAL,
    edge REAL,
    action TEXT,
    recommended_stake REAL,
    kelly_fraction REAL,
    reasoning TEXT,
    context_snapshot TEXT
);

CREATE TABLE IF NOT EXISTS outcomes (
    id INTEGER PRIMARY KEY,
    decision_id INTEGER REFERENCES decisions(id),
    resolved_at TEXT,
    outcome TEXT,
    profit_loss REAL,
    was_correct BOOLEAN
);

CREATE TABLE IF NOT EXISTS calibration_cache (
    id INTEGER PRIMARY KEY,
    updated_at TEXT,
    total_bets INTEGER,
    correct_bets INTEGER,
    accuracy REAL,
    avg_edge REAL,
    roi REAL,
    by_stage TEXT
);
"""


def init_db(conn: sqlite3.Connection | None = None) -> sqlite3.Connection:
    from config import get_db_connection

    own = conn is None
    db = conn or get_db_connection()
    db.executescript(SCHEMA_SQL)
    db.commit()
    if own:
        return db
    return db
