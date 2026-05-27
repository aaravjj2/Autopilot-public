"""Assemble full context dict for the LLM agent."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from calibration.tracker import get_calibration_stats
from features.market_features import parse_market_teams
from features.news_features import detect_injury_keywords, summarize_news
from features.team_features import (
    get_confederation_strength,
    get_h2h_record,
    get_recent_form,
    get_team_tournament_stage_rates,
    get_wc_record,
)
from ingestion.news_fetcher import fetch_team_news


def hours_until(closes_at: str) -> float:
    if not closes_at:
        return 999.0
    try:
        dt = datetime.fromisoformat(closes_at.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        delta = dt - datetime.now(timezone.utc)
        return max(0.0, delta.total_seconds() / 3600.0)
    except ValueError:
        return 999.0


def _injury_fmt(alerts: list[str]) -> str:
    if not alerts:
        return ""
    return "Injury alerts: " + ", ".join(alerts)


def assemble_context(
    market: dict[str, Any],
    bankroll: float,
    open_positions: list[Any],
    db_conn=None,
) -> dict[str, Any]:
    teams = parse_market_teams(market.get("question") or "")
    home_team = teams[0] or market.get("home_team") or "Unknown"
    away_team = teams[1] or market.get("away_team") or "Unknown"

    home_news_raw = fetch_team_news(home_team) if home_team != "Unknown" else []
    away_news_raw = fetch_team_news(away_team) if away_team != "Unknown" else []

    stats = get_calibration_stats(db_conn)

    return {
        "question": market.get("question"),
        "platform": market.get("platform"),
        "market_id": market.get("market_id"),
        "implied_prob": float(market.get("implied_prob") or 0.5),
        "time_to_close_hours": hours_until(str(market.get("closes_at") or "")),
        "volume": float(market.get("volume") or 0),
        "open_interest": float(market.get("open_interest") or 0),
        "closes_at": market.get("closes_at"),
        "home_team": home_team,
        "home_wc_record": get_wc_record(home_team),
        "home_recent_form": get_recent_form(home_team, n=10),
        "home_stage_rates": get_team_tournament_stage_rates(home_team),
        "home_confederation": get_confederation_strength(home_team),
        "home_news": summarize_news(home_news_raw),
        "home_injury_alerts": detect_injury_keywords(home_news_raw, home_team),
        "home_injury_alerts_formatted": _injury_fmt(
            detect_injury_keywords(home_news_raw, home_team)
        ),
        "away_team": away_team,
        "away_wc_record": get_wc_record(away_team),
        "away_recent_form": get_recent_form(away_team, n=10),
        "away_stage_rates": get_team_tournament_stage_rates(away_team),
        "away_confederation": get_confederation_strength(away_team),
        "away_news": summarize_news(away_news_raw),
        "away_injury_alerts": detect_injury_keywords(away_news_raw, away_team),
        "away_injury_alerts_formatted": _injury_fmt(
            detect_injury_keywords(away_news_raw, away_team)
        ),
        "h2h": get_h2h_record(home_team, away_team),
        "bankroll": bankroll,
        "open_positions": open_positions,
        "open_positions_count": len(open_positions),
        "max_stake": bankroll * 0.05,
        "historical_edge": stats,
    }


def context_to_json(ctx: dict[str, Any]) -> str:
    return json.dumps(ctx, default=str)
