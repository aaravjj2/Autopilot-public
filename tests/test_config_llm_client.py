from __future__ import annotations

from apex.core.config import Settings
from apex.core.llm_routing import LlmRoute


def test_get_llm_client_returns_none_for_empty_base_url(monkeypatch) -> None:
    def _fake_route(_: Settings) -> LlmRoute:
        return LlmRoute(
            provider="groq",
            api_key="demo-key",
            base_url="",
            model="m",
            deep_think_model="m",
            quick_think_model="m",
            label="groq",
        )

    monkeypatch.setattr("apex.core.llm_routing.resolve_llm_route", _fake_route)
    settings = Settings(_env_file=None)
    assert settings.get_llm_client() is None


def test_get_llm_client_returns_none_for_empty_non_ollama_key(monkeypatch) -> None:
    def _fake_route(_: Settings) -> LlmRoute:
        return LlmRoute(
            provider="openai",
            api_key="",
            base_url="https://api.openai.com/v1",
            model="m",
            deep_think_model="m",
            quick_think_model="m",
            label="openai",
        )

    monkeypatch.setattr("apex.core.llm_routing.resolve_llm_route", _fake_route)
    settings = Settings(_env_file=None)
    assert settings.get_llm_client() is None


def test_brightdata_enabled_rejects_placeholder_values() -> None:
    assert Settings(BRIGHTDATA_API_KEY="changeme", _env_file=None).brightdata_enabled is False
    assert (
        Settings(BRIGHTDATA_API_KEY="your_api_key_here", _env_file=None).brightdata_enabled
        is False
    )
    assert Settings(BRIGHTDATA_API_KEY="real-token", _env_file=None).brightdata_enabled is True
