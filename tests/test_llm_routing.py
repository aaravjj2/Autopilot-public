"""LLM auto-routing tests."""

from __future__ import annotations


import pytest


def test_resolve_prefers_groq(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_AUTO_ROUTING", "true")
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_KEY", raising=False)

    from apex.core.config import get_settings
    from apex.core.llm_routing import resolve_llm_route

    get_settings.cache_clear()
    route = resolve_llm_route()
    assert route is not None
    assert route.label == "groq"
    assert route.api_key == "test-groq-key"
