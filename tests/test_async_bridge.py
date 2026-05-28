from __future__ import annotations

import pytest

from apex.core.async_bridge import run_sync


async def _value() -> int:
    return 42


def test_run_sync_without_running_loop() -> None:
    assert run_sync(_value()) == 42


@pytest.mark.asyncio
async def test_run_sync_with_running_loop() -> None:
    # Should execute safely even when called from an active event loop thread.
    assert run_sync(_value()) == 42

