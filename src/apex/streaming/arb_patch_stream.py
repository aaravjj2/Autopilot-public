"""WebSocket arb stream with JSON Patch deltas (Week 1 Day 3)."""

from __future__ import annotations

import time
from typing import Any, Callable, Optional


class ArbPatchStream:
    """Tracks last snapshot and emits patch or full-sync messages."""

    def __init__(self) -> None:
        self._previous: list[dict[str, Any]] = []

    def reset(self) -> None:
        self._previous = []

    def build_message(
        self,
        opportunities: list[dict[str, Any]],
        *,
        force_full: bool = False,
    ) -> dict[str, Any]:
        from apex.streaming.arb_patch_diff import diff_opportunities

        ts = int(time.time())
        if force_full or not self._previous:
            self._previous = [dict(o) for o in opportunities]
            return {
                "type": "sync",
                "timestamp": ts,
                "opportunities": self._previous,
            }

        patches = diff_opportunities(self._previous, opportunities)
        self._previous = [dict(o) for o in opportunities]

        if not patches:
            return {"type": "heartbeat", "timestamp": ts}

        return {"type": "patch", "timestamp": ts, "patches": patches}

    async def stream_loop(
        self,
        websocket: Any,
        fetch_opportunities: Callable[[], list[dict[str, Any]]],
        *,
        poll_sec: float = 2.0,
        on_status: Optional[Callable[[list[dict[str, Any]]], dict[str, Any]]] = None,
    ) -> None:
        """Poll fetcher and send patch/sync messages until disconnect."""
        import asyncio

        while True:
            rows = fetch_opportunities()
            msg = self.build_message(rows)
            await websocket.send_json(msg)
            if on_status:
                await websocket.send_json(on_status(rows))
            if msg["type"] == "heartbeat":
                await asyncio.sleep(poll_sec)
                continue
            await asyncio.sleep(poll_sec)
