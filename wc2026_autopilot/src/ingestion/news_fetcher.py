"""Google News RSS fetcher — no API key."""

from __future__ import annotations

import hashlib
from typing import Any
from urllib.parse import quote_plus

import feedparser
import requests

from config import get_logger, ttl_cache

LOGGER = get_logger(__name__)

RSS_BASE = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
_ARTICLE_CACHE: dict[str, list[dict[str, Any]]] = {}


def _cache_key(team: str, query_type: str) -> str:
    return hashlib.md5(f"{team}:{query_type}".encode()).hexdigest()


@ttl_cache(1800)
def _fetch_rss(query: str) -> list[dict[str, Any]]:
    url = RSS_BASE.format(query=quote_plus(query))
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        parsed = feedparser.parse(resp.content)
    except Exception as exc:
        LOGGER.warning("Google News RSS failed for %r: %s", query, exc)
        return []
    articles: list[dict[str, Any]] = []
    for entry in parsed.entries or []:
        articles.append(
            {
                "title": str(getattr(entry, "title", "") or ""),
                "source": str(getattr(getattr(entry, "source", None), "title", "") or "Google News"),
                "published_at": str(getattr(entry, "published", "") or getattr(entry, "updated", "")),
                "url": str(getattr(entry, "link", "") or ""),
                "description": str(getattr(entry, "summary", "") or ""),
            }
        )
    return articles


def fetch_team_news(team: str) -> list[dict[str, Any]]:
    queries = [
        (f"{team} injury lineup", "injury"),
        (f"{team} form training", "form"),
        (f"FIFA World Cup {team}", "preview"),
    ]
    seen: set[str] = set()
    merged: list[dict[str, Any]] = []
    for q, qtype in queries:
        ck = _cache_key(team, qtype)
        if ck in _ARTICLE_CACHE:
            batch = _ARTICLE_CACHE[ck]
        else:
            batch = _fetch_rss(q)
            _ARTICLE_CACHE[ck] = batch
        for art in batch:
            url = art.get("url") or ""
            if url and url in seen:
                continue
            if url:
                seen.add(url)
            merged.append(art)
    return merged


def fetch_match_news(team_a: str, team_b: str) -> list[dict[str, Any]]:
    articles = _fetch_rss(f"FIFA World Cup {team_a} {team_b}")
    return fetch_team_news(team_a) + fetch_team_news(team_b) + articles
