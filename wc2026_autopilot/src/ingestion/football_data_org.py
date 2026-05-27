"""football-data.org free API (optional)."""

from __future__ import annotations

import os
import time
from typing import Any

import requests

from config import bootstrap_env, get_logger

LOGGER = get_logger(__name__)
BASE = "https://api.football-data.org/v4"


class TokenBucket:
    def __init__(self, rate_per_min: float = 10.0) -> None:
        self.capacity = rate_per_min
        self.tokens = rate_per_min
        self.updated = time.monotonic()

    def consume(self) -> None:
        now = time.monotonic()
        elapsed = now - self.updated
        self.updated = now
        self.tokens = min(self.capacity, self.tokens + elapsed * (self.capacity / 60.0))
        if self.tokens < 1:
            sleep_for = (1 - self.tokens) * (60.0 / self.capacity)
            time.sleep(max(0.0, sleep_for))
            self.tokens = 0
        else:
            self.tokens -= 1


_BUCKET = TokenBucket()


def _api_key() -> str:
    bootstrap_env()
    return (os.getenv("FOOTBALL_DATA_API_KEY") or "").strip()


def _get(path: str) -> dict[str, Any]:
    key = _api_key()
    if not key:
        return {}
    _BUCKET.consume()
    try:
        resp = requests.get(
            f"{BASE}{path}",
            headers={"X-Auth-Token": key},
            timeout=20,
        )
        if resp.status_code == 429:
            time.sleep(6)
            resp = requests.get(
                f"{BASE}{path}",
                headers={"X-Auth-Token": key},
                timeout=20,
            )
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        LOGGER.warning("football-data.org %s failed: %s", path, exc)
        return {}


def fetch_wc_matches() -> list[dict[str, Any]]:
    data = _get("/competitions/WC/matches")
    return list(data.get("matches") or [])


def fetch_wc_standings() -> dict[str, Any]:
    return _get("/competitions/WC/standings")


def fetch_wc_teams() -> list[dict[str, Any]]:
    data = _get("/competitions/WC/teams")
    return list(data.get("teams") or [])
