"""Lightweight checks for dashboard integration probes."""

from __future__ import annotations

import pytest

from apex.dashboard.health import _probe_llm_route


def test_llm_route_ok_in_heuristic_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_KEY", raising=False)
    monkeypatch.setenv("LLM_ENABLE_GEMINI", "false")
    monkeypatch.setenv("OLLAMA_HOST", "http://127.0.0.1:1")
    from apex.core.config import Settings

    s = Settings.model_construct(llm_provider="groq", llm_model="llama-3.3-70b-versatile")
    row = _probe_llm_route(s)
    assert row.status == "ok"
    assert "heuristic" in row.detail.lower()


def test_llm_route_ok_when_groq_key_present(monkeypatch: pytest.MonkeyPatch) -> None:
    from types import SimpleNamespace

    from apex.core.config import Settings

    fake_brain = SimpleNamespace(is_live=True, route_label="groq")
    monkeypatch.setattr(
        "apex.brain.finance_brain.FinanceBrain",
        lambda _settings: fake_brain,
    )
    s = Settings.model_construct(llm_provider="groq", llm_model="x")
    row = _probe_llm_route(s)
    assert row.status == "ok"
    assert "groq" in row.detail.lower()
