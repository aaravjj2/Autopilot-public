from __future__ import annotations

import asyncio
import json

try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())
from typing import AsyncIterator, Callable, Dict, Optional

from apex.core.config import get_settings


class ThesisClient:
    """ThesisClient provides an interface to stream thesis text tokens via SSE.

    By default this uses a local mock streamer; real backends can be plugged by
    providing `streamer_fn` that returns an async iterator of strings.
    """

    def __init__(self, streamer_fn: Optional[Callable[..., AsyncIterator[str]]] = None):
        self.settings = get_settings()
        self._streamer_fn = streamer_fn or self._mock_streamer

    async def _mock_streamer(self, prompt: str) -> AsyncIterator[str]:
        # Very small demo streamer that yields chunks with delays
        chunks = [
            "Thesis: The detected divergence appears meaningful.",
            " Kalshi shows YES at 0.92 while Polymarket implies YES at 0.05,",
            " producing a gross cost of ~0.97, after fees a net edge near 0.0.",
            " Recommendation: low confidence; require settlement audit before execution.",
        ]
        for c in chunks:
            await asyncio.sleep(0.05)
            yield c

    async def stream_thesis(self, prompt: str) -> AsyncIterator[str]:
        async for token in self._streamer_fn(prompt):
            yield token

    async def stream_thesis_json(self, prompt: str) -> AsyncIterator[Dict]:
        async for token in self.stream_thesis(prompt):
            yield {"token": token}
