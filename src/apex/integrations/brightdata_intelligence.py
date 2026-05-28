from __future__ import annotations

# BRIGHTDATA INTEGRATION — 2026-05-27 — intelligence service facade

import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse
import json

from apex.core.config import Settings
from apex.core.logging import get_logger
from apex.integrations.brightdata_mcp_client import BrightDataMcpClient

LOGGER = get_logger(__name__)

RISK_KEYWORDS = [
    "postponed",
    "delayed",
    "cancelled",
    "reversed",
    "suspended",
    "investigation",
    "unexpected",
    "surprise",
    "breaking",
    "halt",
    "freeze",
    "appeal",
    "lawsuit",
    "injunction",
]

AUTHORITATIVE_SOURCE_DOMAINS: dict[str, tuple[str, ...]] = {
    "bls": ("bls.gov",),
    "cpi": ("bls.gov",),
    "fomc": ("federalreserve.gov",),
    "fed": ("federalreserve.gov",),
    "coingecko": ("coingecko.com",),
    "census": ("census.gov",),
    "eia": ("eia.gov",),
    "treasury": ("treasury.gov",),
    "sec": ("sec.gov",),
}


class BrightDataIntelligence:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client = BrightDataMcpClient(settings)
        self._request_count = 0

    async def _call_mcp_tool(self, tool: str, params: dict[str, Any]) -> Any:
        """Single MCP call choke-point with hard request cap and soft-fail behavior."""
        if not self._client.is_configured():
            return None
        if self._request_count >= self.settings.brightdata_max_requests_per_run:
            LOGGER.warning("BrightData request cap reached (%s)", self._request_count)
            return None
        self._request_count += 1
        try:
            return await self._client.call_tool(tool, params)
        except Exception as exc:
            LOGGER.warning("BrightData MCP call failed (tool=%s): %s", tool, exc)
            return None

    @staticmethod
    def _extract_links(markdown: str) -> list[dict[str, str]]:
        out: list[dict[str, str]] = []
        for m in re.finditer(r"\[([^\]]+)\]\((https?://[^)]+)\)", markdown or ""):
            out.append({"title": m.group(1).strip(), "url": m.group(2).strip(), "snippet": ""})
        return out

    @staticmethod
    def _domain(url: str) -> str:
        try:
            return (urlparse(url).hostname or "").lower()
        except Exception:
            return ""

    def _allowed_domains_for_keywords(self, source_keywords: list[str]) -> tuple[str, ...]:
        domains: list[str] = []
        for kw in source_keywords:
            key = (kw or "").strip().lower()
            if key in AUTHORITATIVE_SOURCE_DOMAINS:
                domains.extend(AUTHORITATIVE_SOURCE_DOMAINS[key])
        return tuple(dict.fromkeys(domains))

    def _is_authoritative_source(self, url: str, source_keywords: list[str]) -> bool:
        domain = self._domain(url)
        allowed = self._allowed_domains_for_keywords(source_keywords)
        if not allowed:
            return False
        return any(domain == d or domain.endswith(f".{d}") for d in allowed)

    async def search_breaking_news(self, query: str, n_results: int = 5) -> list[dict]:
        if not isinstance(query, str) or not query.strip():
            return []
        n_results = max(1, min(n_results, 10))
        try:
            _ = await self.check_session_budget()
            # Prefer discover when available: it returns relevance-ranked structured results.
            tool = "discover"
            has_discover = False
            try:
                has_discover = await self._client.has_tool(tool)
            except Exception:
                has_discover = False
            if not has_discover:
                tool = "search_engine"

            if tool == "discover":
                payload = await self._call_mcp_tool(
                    "discover",
                    {"query": query.strip(), "num_results": n_results, "remove_duplicates": True},
                )
            else:
                payload = await self._call_mcp_tool("search_engine", {"query": query.strip(), "engine": "google"})
            if payload is None:
                return []
            if isinstance(payload, str):
                s = payload.strip()
                if s.startswith("{") or s.startswith("["):
                    try:
                        payload = json.loads(s)
                    except Exception:
                        pass

            # discover: list of {link,title,description,relevance_score}
            if isinstance(payload, list):
                out: list[dict[str, str]] = []
                for item in payload:
                    if not isinstance(item, dict):
                        continue
                    out.append(
                        {
                            "title": str(item.get("title", "")),
                            "url": str(item.get("link", "")),
                            "snippet": str(item.get("description", "")),
                        }
                    )
                return [x for x in out if x.get("title") or x.get("url")][:n_results]

            # search_engine: {organic:[{link,title,description}]}
            if isinstance(payload, dict) and isinstance(payload.get("organic"), list):
                out2: list[dict[str, str]] = []
                for item in payload["organic"]:
                    if not isinstance(item, dict):
                        continue
                    out2.append(
                        {
                            "title": str(item.get("title", "")),
                            "url": str(item.get("link", "")),
                            "snippet": str(item.get("description", "")),
                        }
                    )
                return [x for x in out2 if x.get("title") or x.get("url")][:n_results]

            text = payload if isinstance(payload, str) else str(payload)
            links = self._extract_links(text)
            return links[:n_results]
        except Exception as exc:
            LOGGER.warning("BrightData search failed for %r: %s", query, exc)
            return []

    async def scrape_source_page(self, url: str) -> str:
        try:
            parsed = urlparse(url)
            if parsed.scheme not in {"http", "https"}:
                return ""
        except Exception:
            return ""
        try:
            payload = await self._call_mcp_tool("scrape_as_markdown", {"url": url})
            if payload is None:
                return ""
            text = payload if isinstance(payload, str) else str(payload)
            return text[:8000]
        except Exception:
            return ""

    async def get_settlement_source(
        self, event_description: str, source_keywords: list[str]
    ) -> dict:
        try:
            if not self._client.is_configured():
                return {"found": False, "url": "", "excerpt": "", "confidence": 0.0}
            kw = (source_keywords[0] if source_keywords else "").strip()
            allowed_domains = self._allowed_domains_for_keywords(source_keywords)
            # Strong template: search authority-first with site filter when possible.
            query = f"{event_description} official {kw} data release".strip()
            if allowed_domains:
                query = f"{query} site:{allowed_domains[0]}".strip()
            news = await self.search_breaking_news(query, n_results=5)
            if not news and allowed_domains:
                # Fallback: retry without site restriction in case authority host filtering is over-constrained.
                fallback_query = f"{event_description} official {kw} data release".strip()
                news = await self.search_breaking_news(fallback_query, n_results=5)
            if not news:
                return {"found": False, "url": "", "excerpt": "", "confidence": 0.0}
            # Prefer authoritative domain hits when present.
            top = next(
                (item for item in news if self._is_authoritative_source(str(item.get("url", "")), source_keywords)),
                news[0],
            )
            url = str(top.get("url", "")).strip()
            if not url:
                return {"found": False, "url": "", "excerpt": "", "confidence": 0.0}
            markdown = await self.scrape_source_page(url)
            excerpt_base = markdown or str(top.get("snippet", ""))
            excerpt = excerpt_base[:500]
            if not excerpt.strip():
                return {"found": False, "url": "", "excerpt": "", "confidence": 0.0}
            conf = 0.9 if self._is_authoritative_source(url, source_keywords) else 0.5
            return {"found": True, "url": url, "excerpt": excerpt, "confidence": conf}
        except Exception:
            return {"found": False, "url": "", "excerpt": "", "confidence": 0.0}

    async def get_market_context(
        self, kalshi_title: str, poly_question: str, horizon_hours: float
    ) -> dict:
        if horizon_hours <= 2:
            return {
                "news": [],
                "risk_signals": [],
                "data_freshness": datetime.now(timezone.utc).isoformat(),
            }
        news = await self.search_breaking_news(f"{kalshi_title} latest news", n_results=5)
        signals: list[str] = []
        for item in news:
            blob = f"{item.get('title','')} {item.get('snippet','')}".lower()
            for kw in RISK_KEYWORDS:
                if kw in blob:
                    signals.append(kw)
        return {
            "news": news,
            "risk_signals": sorted(set(signals)),
            "data_freshness": datetime.now(timezone.utc).isoformat(),
        }

    async def get_wc_match_live_state(self, home_team: str, away_team: str) -> dict:
        news = await self.search_breaking_news(f"{home_team} vs {away_team} live score", 5)
        preferred = next(
            (
                n
                for n in news
                if any(host in str(n.get("url", "")).lower() for host in ("espn.", "bbc.", "bbc.co"))
            ),
            news[0] if news else {},
        )
        url = str(preferred.get("url", ""))
        text = await self.scrape_source_page(url) if url else ""
        if not text:
            text = " ".join(f"{n.get('title','')} {n.get('snippet','')}" for n in news)
        score = re.search(r"(\d+)\s*[-–]\s*(\d+)", text)
        minute = re.search(r"(\d+)'", text)
        return {
            "home_score": int(score.group(1)) if score else 0,
            "away_score": int(score.group(2)) if score else 0,
            "minute": int(minute.group(1)) if minute else 0,
            "period": "LIVE" if minute else "PRE",
            "events": [],
            "injuries": [],
        }

    async def check_session_budget(self, warn_at_requests: int = 40) -> dict:
        # Use internal counter as the hard cap; not all Bright Data MCP deployments expose session_stats.
        calls_made = self._request_count
        calls_remaining = max(self.settings.brightdata_max_requests_per_run - calls_made, 0)
        ok = calls_made < self.settings.brightdata_max_requests_per_run
        if calls_made > warn_at_requests:
            LOGGER.warning("BrightData session approaching cap: %s calls", calls_made)
        return {
            "calls_made": calls_made,
            "calls_remaining": calls_remaining,
            "ok": ok,
        }
