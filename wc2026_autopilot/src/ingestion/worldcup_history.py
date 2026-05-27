"""Download Fjelstul World Cup Database CSVs + international results."""

from __future__ import annotations

import csv
import io
import sqlite3
from dataclasses import dataclass
from typing import Iterator

from config import download_text, get_logger

LOGGER = get_logger(__name__)

FJELSTUL_BASE = "https://raw.githubusercontent.com/jfjelstul/worldcup/master/data-csv"
FJELSTUL_FILES = (
    "matches.csv",
    "teams.csv",
    "goals.csv",
    "bookings.csv",
    "player_appearances.csv",
)
INTL_RESULTS_URLS = (
    "https://raw.githubusercontent.com/martj42/international_results/master/results.csv",
    "https://raw.githubusercontent.com/martj42/international_results/main/results.csv",
)


@dataclass
class WcMatchRow:
    tournament_year: int
    stage: str
    home_team: str
    away_team: str
    home_goals: int
    away_goals: int
    home_goals_extra: int
    away_goals_extra: int
    winner: str
    date: str
    venue: str


def _iter_csv(text: str) -> Iterator[dict[str, str]]:
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        yield {k.strip(): (v or "").strip() for k, v in row.items()}


def download_fjelstul_csvs() -> dict[str, str]:
    out: dict[str, str] = {}
    for name in FJELSTUL_FILES:
        url = f"{FJELSTUL_BASE}/{name}"
        out[name] = download_text(url, dest_name=f"fjelstul_{name}")
        LOGGER.info("Downloaded %s (%d bytes)", name, len(out[name]))
    return out


def download_international_results() -> str:
    last_err: Exception | None = None
    for url in INTL_RESULTS_URLS:
        try:
            return download_text(url, dest_name="international_results.csv")
        except Exception as exc:
            last_err = exc
            LOGGER.warning("International results URL failed %s: %s", url, exc)
    if last_err:
        raise last_err
    raise RuntimeError("No international results URL available")


def parse_matches_csv(text: str) -> list[WcMatchRow]:
    rows: list[WcMatchRow] = []
    for r in _iter_csv(text):
        year_raw = r.get("year") or r.get("tournament_year") or r.get("Year") or "0"
        try:
            year = int(float(year_raw))
        except ValueError:
            year = 0
        if year == 0:
            # jfjelstul/worldcup data-csv uses tournament_name / tournament_id (e.g. "1930 FIFA ...", "WC-1930")
            import re

            hint = str(r.get("tournament_name") or r.get("tournament_id") or "")
            m = re.search(r"(\d{4})", hint)
            if m:
                try:
                    year = int(m.group(1))
                except ValueError:
                    year = 0
        home = r.get("home_team") or r.get("home_team_name") or r.get("home") or ""
        away = r.get("away_team") or r.get("away_team_name") or r.get("away") or ""
        if not home or not away:
            continue

        def _int(key: str, default: int = 0) -> int:
            try:
                return int(float(r.get(key) or default))
            except ValueError:
                return default

        hg = _int("home_team_score", _int("home_score", _int("score_home")))
        ag = _int("away_team_score", _int("away_score", _int("score_away")))
        winner = r.get("winning_team") or r.get("winner") or ""
        if not winner:
            if hg > ag:
                winner = home
            elif ag > hg:
                winner = away
            else:
                winner = "draw"
        rows.append(
            WcMatchRow(
                tournament_year=year,
                stage=(r.get("stage_name") or r.get("stage") or "group").lower(),
                home_team=home,
                away_team=away,
                home_goals=hg,
                away_goals=ag,
                home_goals_extra=_int("home_team_extra_time_score"),
                away_goals_extra=_int("away_team_extra_time_score"),
                winner=winner,
                date=r.get("match_date") or r.get("date") or "",
                venue=r.get("stadium_name") or r.get("venue") or "",
            )
        )
    return rows


def insert_wc_matches(conn: sqlite3.Connection, rows: list[WcMatchRow]) -> int:
    conn.execute("DELETE FROM wc_matches")
    conn.executemany(
        """
        INSERT INTO wc_matches (
            tournament_year, stage, home_team, away_team,
            home_goals, away_goals, home_goals_extra, away_goals_extra,
            winner, date, venue
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                r.tournament_year,
                r.stage,
                r.home_team,
                r.away_team,
                r.home_goals,
                r.away_goals,
                r.home_goals_extra,
                r.away_goals_extra,
                r.winner,
                r.date,
                r.venue,
            )
            for r in rows
        ],
    )
    conn.commit()
    return len(rows)


def insert_international_results(conn: sqlite3.Connection, text: str) -> int:
    conn.execute("DELETE FROM international_results")
    batch: list[tuple] = []
    for r in _iter_csv(text):
        home = r.get("home_team") or r.get("HomeTeam") or ""
        away = r.get("away_team") or r.get("AwayTeam") or ""
        if not home or not away:
            continue
        try:
            hs = int(float(r.get("home_score") or r.get("home_goals") or 0))
            aws = int(float(r.get("away_score") or r.get("away_goals") or 0))
        except ValueError:
            continue
        neutral_raw = (r.get("neutral") or r.get("Neutral") or "false").lower()
        batch.append(
            (
                r.get("date") or r.get("Date") or "",
                home,
                away,
                hs,
                aws,
                r.get("tournament") or r.get("Tournament") or "",
                neutral_raw in ("1", "true", "yes"),
            )
        )
    conn.executemany(
        """
        INSERT INTO international_results
        (date, home_team, away_team, home_score, away_score, tournament, neutral)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        batch,
    )
    conn.commit()
    return len(batch)


def load_all(conn: sqlite3.Connection) -> dict[str, int]:
    csvs = download_fjelstul_csvs()
    matches = parse_matches_csv(csvs["matches.csv"])
    wc_n = insert_wc_matches(conn, matches)
    intl_text = download_international_results()
    intl_n = insert_international_results(conn, intl_text)
    return {"wc_matches": wc_n, "international_results": intl_n}
