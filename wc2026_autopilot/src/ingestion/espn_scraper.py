"""ESPN hidden soccer API — no key required."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import requests

from config import get_logger, ttl_cache

LOGGER = get_logger(__name__)

SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"
NEWS_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/news"
STANDINGS_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/standings"
TEAM_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/teams/{team_id}"

_DISK_CACHE: dict[str, Any] = {}


@dataclass
class EspnMatch:
    id: str
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    status: str
    date: str


@dataclass
class EspnNews:
    title: str
    description: str
    published: str
    url: str


@dataclass
class EspnStandings:
    groups: list[dict[str, Any]] = field(default_factory=list)


def _get_json(url: str, cache_key: str) -> dict[str, Any]:
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code != 200:
            LOGGER.warning("ESPN %s returned %s", url, resp.status_code)
            if cache_key in _DISK_CACHE:
                return _DISK_CACHE[cache_key]
            return {}
        data = resp.json()
        _DISK_CACHE[cache_key] = data
        return data
    except Exception as exc:
        LOGGER.warning("ESPN fetch failed %s: %s", url, exc)
        return _DISK_CACHE.get(cache_key, {})


@ttl_cache(300)
def fetch_scoreboard() -> list[EspnMatch]:
    data = _get_json(SCOREBOARD_URL, "scoreboard")
    out: list[EspnMatch] = []
    for ev in data.get("events") or []:
        comps = (ev.get("competitions") or [{}])[0]
        competitors = comps.get("competitors") or []
        home = away = ""
        hs = aws = 0
        for c in competitors:
            name = (c.get("team") or {}).get("displayName") or ""
            score = int(c.get("score") or 0)
            if c.get("homeAway") == "home":
                home, hs = name, score
            else:
                away, aws = name, score
        out.append(
            EspnMatch(
                id=str(ev.get("id") or ""),
                home_team=home,
                away_team=away,
                home_score=hs,
                away_score=aws,
                status=(ev.get("status") or {}).get("type", {}).get("description", ""),
                date=str(ev.get("date") or ""),
            )
        )
    return out


@ttl_cache(300)
def fetch_news() -> list[EspnNews]:
    data = _get_json(NEWS_URL, "news")
    articles = data.get("articles") or data.get("headlines") or []
    out: list[EspnNews] = []
    for a in articles:
        out.append(
            EspnNews(
                title=str(a.get("headline") or a.get("title") or ""),
                description=str(a.get("description") or a.get("summary") or ""),
                published=str(a.get("published") or a.get("lastModified") or ""),
                url=str(a.get("links", {}).get("web", {}).get("href") or a.get("link") or ""),
            )
        )
    return out


@ttl_cache(300)
def fetch_standings() -> EspnStandings:
    data = _get_json(STANDINGS_URL, "standings")
    groups: list[dict[str, Any]] = []
    for child in data.get("children") or []:
        groups.append({"name": child.get("name"), "standings": child.get("standings")})
    return EspnStandings(groups=groups)


def fetch_team(team_id: str) -> dict[str, Any]:
    return _get_json(TEAM_URL.format(team_id=team_id), f"team_{team_id}")
