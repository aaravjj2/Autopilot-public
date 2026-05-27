"""Team-level feature engineering from SQLite."""

from __future__ import annotations

import re
from typing import Any

from db.queries import (
    fetch_h2h,
    fetch_recent_international,
    fetch_stage_rows,
    fetch_team_wc_years,
    fetch_wc_matches_for_team,
    get_conn,
)

STAGE_ORDER = {
    "group": 1,
    "round_of_16": 2,
    "round of 16": 2,
    "quarter": 3,
    "quarterfinal": 3,
    "quarter-finals": 3,
    "semi": 4,
    "semifinal": 4,
    "semi-finals": 4,
    "final": 5,
    "third place": 4,
}

CONFED_MAP = {
    "brazil": "CONMEBOL",
    "argentina": "CONMEBOL",
    "france": "UEFA",
    "germany": "UEFA",
    "spain": "UEFA",
    "england": "UEFA",
    "usa": "CONCACAF",
    "mexico": "CONCACAF",
    "japan": "AFC",
    "south korea": "AFC",
    "morocco": "CAF",
    "senegal": "CAF",
}


def _norm(name: str) -> str:
    return re.sub(r"\s+", " ", (name or "").strip().lower())


def _team_match(row_home: str, row_away: str, team: str) -> bool:
    t = _norm(team)
    return t in _norm(row_home) or t in _norm(row_away)


def _best_finish(stage_rows: list[Any]) -> str:
    best = 0
    label = "Group"
    for r in stage_rows:
        stage = _norm(str(r["stage"]))
        if "final" in stage and "semi" not in stage and "quarter" not in stage:
            winner = ""
            try:
                winner = str(r["winner"] or "")
            except Exception:
                winner = ""
            if "win" in _norm(winner):
                return "Champion"
            return "Finalist"
        for key, rank in STAGE_ORDER.items():
            if key in stage:
                if rank > best:
                    best = rank
                    label = key.replace("_", " ").title()
    mapping = {5: "Final", 4: "Semifinal", 3: "Quarterfinal", 2: "Round of 16", 1: "Group"}
    return mapping.get(best, label)


def get_wc_record(team: str) -> dict[str, Any]:
    conn = get_conn()
    rows = fetch_wc_matches_for_team(conn, team)
    if not rows:
        return {
            "appearances": 0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "goals_for": 0,
            "goals_against": 0,
            "best_finish": "N/A",
            "avg_goals_per_game": 0.0,
            "win_rate": 0.0,
        }
    wins = draws = losses = gf = ga = games = 0
    for r in rows:
        home, away = r["home_team"], r["away_team"]
        if not (_team_match(home, away, team)):
            continue
        games += 1
        is_home = _norm(team) in _norm(home)
        tg = int(r["home_goals"] or 0) if is_home else int(r["away_goals"] or 0)
        og = int(r["away_goals"] or 0) if is_home else int(r["home_goals"] or 0)
        gf += tg
        ga += og
        if tg > og:
            wins += 1
        elif tg == og:
            draws += 1
        else:
            losses += 1
    years = fetch_team_wc_years(conn, team)
    return {
        "appearances": len(years) or len(set(r["tournament_year"] for r in rows)),
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals_for": gf,
        "goals_against": ga,
        "best_finish": _best_finish(rows),
        "avg_goals_per_game": round(gf / games, 2) if games else 0.0,
        "win_rate": round(wins / games, 3) if games else 0.0,
    }


def get_h2h_record(team_a: str, team_b: str) -> dict[str, Any]:
    conn = get_conn()
    wc_rows = fetch_h2h(conn, team_a, team_b)
    intl = conn.execute(
        """
        SELECT * FROM international_results
        WHERE (home_team LIKE ? AND away_team LIKE ?)
           OR (home_team LIKE ? AND away_team LIKE ?)
        """,
        (f"%{team_a}%", f"%{team_b}%", f"%{team_b}%", f"%{team_a}%"),
    ).fetchall()
    all_rows = list(wc_rows) + list(intl)
    a_wins = b_wins = draws = a_goals = b_goals = 0
    wc_only: list[str] = []
    for r in all_rows:
        home = r["home_team"]
        away = r["away_team"]
        hs = int(r["home_goals"] if "home_goals" in r.keys() else r["home_score"] or 0)
        aws = int(r["away_goals"] if "away_goals" in r.keys() else r["away_score"] or 0)
        a_home = _norm(team_a) in _norm(home)
        ag = hs if a_home else aws
        bg = aws if a_home else hs
        a_goals += ag
        b_goals += bg
        if ag > bg:
            a_wins += 1
        elif ag < bg:
            b_wins += 1
        else:
            draws += 1
        if "tournament_year" in r.keys():
            wc_only.append(f"{home} {hs}-{aws} {away} ({r['tournament_year']})")
    return {
        "meetings": len(all_rows),
        "team_a_wins": a_wins,
        "team_b_wins": b_wins,
        "draws": draws,
        "team_a_goals": a_goals,
        "team_b_goals": b_goals,
        "wc_meetings_only": wc_only[:10],
    }


def get_recent_form(team: str, n: int = 10) -> dict[str, Any]:
    conn = get_conn()
    rows = fetch_recent_international(conn, team, n)
    wins = draws = losses = gf = ga = 0
    form_chars: list[str] = []
    for r in rows:
        is_home = _norm(team) in _norm(r["home_team"])
        hs = int(r["home_score"] or 0)
        aws = int(r["away_score"] or 0)
        tg = hs if is_home else aws
        og = aws if is_home else hs
        gf += tg
        ga += og
        if tg > og:
            wins += 1
            form_chars.append("W")
        elif tg == og:
            draws += 1
            form_chars.append("D")
        else:
            losses += 1
            form_chars.append("L")
    return {
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals_for": gf,
        "goals_against": ga,
        "form_string": "".join(form_chars) or "N/A",
    }


def get_team_tournament_stage_rates(team: str) -> dict[str, float]:
    conn = get_conn()
    years = fetch_team_wc_years(conn, team)
    if not years:
        return {
            "group_exit_rate": 0.0,
            "r16_rate": 0.0,
            "qf_rate": 0.0,
            "sf_rate": 0.0,
            "final_rate": 0.0,
            "win_rate": 0.0,
        }
    stage_rows = fetch_stage_rows(conn, team)
    apps = max(len(years), 1)
    r16 = qf = sf = final = win = 0
    for yr in years:
        yr_stages = [_norm(str(r["stage"])) for r in stage_rows if r["tournament_year"] == yr]
        joined = " ".join(yr_stages)
        if any(s in joined for s in ("round", "quarter", "semi", "final")):
            r16 += 1
        if any(s in joined for s in ("quarter", "semi", "final")):
            qf += 1
        if any(s in joined for s in ("semi", "final")) and "quarter" not in joined:
            sf += 1
        if "final" in joined and "semi" not in joined and "quarter" not in joined:
            final += 1
        champ_rows = [r for r in stage_rows if r["tournament_year"] == yr]
        if any(_norm(str(r.get("winner", ""))) == _norm(team) for r in champ_rows if "winner" in r.keys()):
            win += 1
    return {
        "group_exit_rate": round(1 - r16 / apps, 3),
        "r16_rate": round(r16 / apps, 3),
        "qf_rate": round(qf / apps, 3),
        "sf_rate": round(sf / apps, 3),
        "final_rate": round(final / apps, 3),
        "win_rate": round(win / apps, 3),
    }


def get_confederation_strength(team: str) -> dict[str, Any]:
    conf = CONFED_MAP.get(_norm(team), "Unknown")
    conn = get_conn()
    rows = conn.execute(
        "SELECT tournament_year, stage, home_team, away_team, winner FROM wc_matches"
    ).fetchall()
    conf_wins = conf_apps = 0
    champions = 0
    for r in rows:
        for side in (r["home_team"], r["away_team"]):
            if CONFED_MAP.get(_norm(side)) == conf:
                conf_apps += 1
                if _norm(str(r["winner"])) == _norm(side):
                    conf_wins += 1
        if _norm(str(r["winner"])) in CONFED_MAP and CONFED_MAP[_norm(str(r["winner"]))] == conf:
            if "final" in _norm(str(r["stage"] or "")):
                champions += 1
    tournaments = len(set(r["tournament_year"] for r in rows)) or 1
    return {
        "confederation": conf,
        "avg_team_wins_per_tournament": round(conf_wins / tournaments, 2),
        "champions_count": champions,
    }
