from __future__ import annotations

import asyncio

from apex.services.thesis_client import ThesisClient


def test_mock_streamer_sync():
    tc = ThesisClient()
    # collect tokens
    tokens = []

    async def collect():
        async for t in tc.stream_thesis("prompt"):
            tokens.append(t)

    asyncio.run(collect())
    assert len(tokens) >= 1
    assert "Thesis:" in tokens[0]
