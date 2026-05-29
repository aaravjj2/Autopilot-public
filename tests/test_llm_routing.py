"""LLM auto-routing tests."""

from __future__ import annotations

import pytest


def test_resolve_prefers_groq(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_AUTO_ROUTING", "true")
    monkeypatch.setenv("LLM_ENABLE_GEMINI", "false")
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    monkeypatch.setenv("GEMINI_API_KEY", "AIzaSy-should-not-win")
    monkeypatch.delenv("OPENROUTER_KEY", raising=False)

    from apex.core.config import get_settings
    from apex.core.llm_routing import resolve_llm_route, resolve_llm_routes

    get_settings.cache_clear()
    route = resolve_llm_route()
    assert route is not None
    assert route.label == "groq"
    assert route.api_key == "test-groq-key"
    routes = resolve_llm_routes()
    assert routes[0].label == "groq"


def test_skips_gemini_unless_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_AUTO_ROUTING", "true")
    monkeypatch.setenv("LLM_ENABLE_GEMINI", "false")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "AIzaSy-only-gemini")
    monkeypatch.delenv("OPENROUTER_KEY", raising=False)
    monkeypatch.setenv("OLLAMA_HOST", "http://127.0.0.1:1")

    from apex.core.config import get_settings
    from apex.core.llm_routing import resolve_llm_routes

    get_settings.cache_clear()
    assert resolve_llm_routes(env_only=True) == []


def test_llm_error_disables_route_on_org_restricted() -> None:
    from apex.core.llm_routing import llm_error_disables_route

    assert llm_error_disables_route(RuntimeError("organization_restricted"))
    assert not llm_error_disables_route(RuntimeError("429 rate limited"))
