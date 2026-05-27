"""Lightweight checks for dashboard integration probes."""

from __future__ import annotations

import pytest

from apex.dashboard.health import _probe_llm_route


def test_llm_route_warns_when_groq_missing_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    from apex.core.config import Settings

    s = Settings.model_construct(llm_provider="groq", llm_model="llama-3.3-70b-versatile")
    row = _probe_llm_route(s)
    assert row.status == "warn"
    assert "GROQ_API_KEY" in row.detail


def test_llm_route_ok_when_groq_key_present(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "dummy-for-test")
    from apex.core.config import Settings

    s = Settings.model_construct(llm_provider="groq", llm_model="x")
    row = _probe_llm_route(s)
    assert row.status == "ok"
