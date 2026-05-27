"""DB read helpers."""

from __future__ import annotations

import sqlite3
from typing import Any


def count_rows(conn: sqlite3.Connection, table: str) -> int:
    row = conn.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()
    return int(row["c"] if row else 0)


def fetch_wc_matches_for_team(conn: sqlite3.Connection, team: str) -> list[sqlite3.Row]:
    like = f"%{team}%"
    return list(
        conn.execute(
            """
            SELECT * FROM wc_matches
            WHERE home_team LIKE ? OR away_team LIKE ?
            ORDER BY date DESC
            """,
            (like, like),
        )
    )


def fetch_h2h(conn: sqlite3.Connection, team_a: str, team_b: str) -> list[sqlite3.Row]:
    return list(
        conn.execute(
            """
            SELECT * FROM wc_matches
            WHERE (home_team LIKE ? AND away_team LIKE ?)
               OR (home_team LIKE ? AND away_team LIKE ?)
            ORDER BY date DESC
            """,
            (f"%{team_a}%", f"%{team_b}%", f"%{team_b}%", f"%{team_a}%"),
        )
    )


def fetch_recent_international(
    conn: sqlite3.Connection, team: str, n: int = 10
) -> list[sqlite3.Row]:
    like = f"%{team}%"
    return list(
        conn.execute(
            """
            SELECT * FROM international_results
            WHERE home_team LIKE ? OR away_team LIKE ?
            ORDER BY date DESC
            LIMIT ?
            """,
            (like, like, n),
        )
    )


def fetch_team_wc_years(conn: sqlite3.Connection, team: str) -> list[int]:
    like = f"%{team}%"
    rows = conn.execute(
        """
        SELECT DISTINCT tournament_year FROM wc_matches
        WHERE home_team LIKE ? OR away_team LIKE ?
        ORDER BY tournament_year
        """,
        (like, like),
    ).fetchall()
    return [int(r["tournament_year"]) for r in rows if r["tournament_year"]]


def fetch_stage_rows(conn: sqlite3.Connection, team: str) -> list[sqlite3.Row]:
    like = f"%{team}%"
    return list(
        conn.execute(
            """
            SELECT tournament_year, stage FROM wc_matches
            WHERE home_team LIKE ? OR away_team LIKE ?
            """,
            (like, like),
        )
    )


def get_conn() -> sqlite3.Connection:
    from config import get_db_connection
    from db.schema import init_db

    conn = get_db_connection()
    init_db(conn)
    return conn
