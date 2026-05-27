"""L2 orderbook ingestion into Redis HSET (Week 1 Day 1)."""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from apex.cache.redis_client import get_redis, memory_hgetall, memory_hset

LOGGER = logging.getLogger(__name__)

DEFAULT_LEVELS = 5
TTL_SEC = 300


def orderbook_key(venue: str, ticker: str) -> str:
    return f"orderbook:{venue}:{ticker}"


def ingest_orderbook(
    venue: str,
    ticker: str,
    book: dict[str, Any],
    *,
    levels: int = DEFAULT_LEVELS,
    redis_url: Optional[str] = None,
) -> dict[str, str]:
    """Write top-N bid levels per side to Redis HSET."""
    key = orderbook_key(venue, ticker)
    mapping: dict[str, str] = {
        "venue": venue,
        "ticker": ticker,
        "meta": json.dumps({"levels": levels}),
    }

    for side in ("yes", "no"):
        ladder = book.get(side) or book.get(f"{side}_bids") or []
        if isinstance(ladder, dict):
            ladder = list(ladder.items())
        for i, level in enumerate(ladder[:levels]):
            if isinstance(level, (list, tuple)) and len(level) >= 2:
                price, qty = level[0], level[1]
            elif isinstance(level, dict):
                price = level.get("price", level.get("p", 0))
                qty = level.get("qty", level.get("quantity", 0))
            else:
                continue
            mapping[f"{side}:{i}:price"] = str(price)
            mapping[f"{side}:{i}:qty"] = str(qty)

    client = get_redis(redis_url if redis_url is not None else None)
    if client is not None:
        pipe = client.pipeline()
        pipe.delete(key)
        if mapping:
            pipe.hset(key, mapping=mapping)
        pipe.expire(key, TTL_SEC)
        pipe.execute()
    else:
        memory_hset(key, mapping)

    return mapping


def read_orderbook(
    venue: str,
    ticker: str,
    *,
    redis_url: Optional[str] = None,
) -> dict[str, Any]:
    """Read L2 book from Redis HSET."""
    key = orderbook_key(venue, ticker)
    client = get_redis(redis_url if redis_url is not None else None)
    if client is not None:
        raw = client.hgetall(key)
    else:
        raw = memory_hgetall(key)

    if not raw:
        return {}

    result: dict[str, Any] = {"venue": raw.get("venue"), "ticker": raw.get("ticker"), "yes": [], "no": []}
    for side in ("yes", "no"):
        i = 0
        while f"{side}:{i}:price" in raw:
            result[side].append(
                [float(raw[f"{side}:{i}:price"]), float(raw[f"{side}:{i}:qty"])]
            )
            i += 1
    return result
