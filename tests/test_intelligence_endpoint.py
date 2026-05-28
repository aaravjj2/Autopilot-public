from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException

import backend_api


@pytest.mark.asyncio
async def test_run_intelligence_report_blocks_duplicate_inflight(monkeypatch) -> None:
    async def _slow(_ticker: str) -> None:
        await asyncio.sleep(0.2)
        backend_api._INTEL_IN_FLIGHT.discard(_ticker)

    monkeypatch.setattr(backend_api, "_run_intelligence_for_ticker", _slow)
    monkeypatch.delenv("INTELLIGENCE_RUN_TOKEN", raising=False)
    original_demo_mode = backend_api.settings.demo_mode
    backend_api._INTEL_IN_FLIGHT.clear()
    try:
        object.__setattr__(backend_api.settings, "demo_mode", True)
        out = await backend_api.run_intelligence_report(
            "cpi-test",
            x_intelligence_override="allow-demo-credits",
            x_intelligence_token=None,
        )
        assert out["accepted"] is True
        with pytest.raises(HTTPException) as exc:
            await backend_api.run_intelligence_report(
                "cpi-test",
                x_intelligence_override="allow-demo-credits",
                x_intelligence_token=None,
            )
        assert exc.value.status_code == 409
        await asyncio.sleep(0.25)
    finally:
        object.__setattr__(backend_api.settings, "demo_mode", original_demo_mode)
        backend_api._INTEL_IN_FLIGHT.clear()
