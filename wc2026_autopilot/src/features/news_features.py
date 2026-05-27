"""News headline features."""

from __future__ import annotations

import re
from typing import Any

INJURY_KEYWORDS = ["injured", "doubt", "out", "miss", "ruled out", "withdrawn"]


def summarize_news(articles: list[dict[str, Any]], max_items: int = 5) -> str:
    seen_titles: set[str] = set()
    bullets: list[str] = []
    for art in articles:
        title = (art.get("title") or "").strip()
        if not title:
            continue
        key = title.lower()[:80]
        if key in seen_titles:
            continue
        seen_titles.add(key)
        src = art.get("source") or "News"
        pub = art.get("published_at") or art.get("published") or ""
        bullets.append(f"• {src}: {title} ({pub})")
        if len(bullets) >= max_items:
            break
    return "\n".join(bullets) if bullets else "• No recent headlines found."


def detect_injury_keywords(articles: list[dict[str, Any]], team: str) -> list[str]:
    found: list[str] = []
    name_pattern = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b")
    for art in articles:
        text = f"{art.get('title', '')} {art.get('description', '')}".lower()
        if not any(kw in text for kw in INJURY_KEYWORDS):
            continue
        for match in name_pattern.findall(f"{art.get('title', '')} {art.get('description', '')}"):
            if match.lower() in (team.lower(), "world", "cup", "fifa"):
                continue
            if match not in found:
                found.append(match)
    return found[:10]
