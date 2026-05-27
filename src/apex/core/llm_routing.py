"""Automatic LLM provider selection: Groq → Gemini → OpenRouter → Ollama."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

import logging

if TYPE_CHECKING:
    from apex.core.config import Settings

LOGGER = logging.getLogger(__name__)

DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"
DEFAULT_GROQ_QUICK = "llama-3.1-8b-instant"
DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"
DEFAULT_OPENROUTER_MODEL = "meta-llama/llama-3.3-70b-instruct:free"
DEFAULT_OLLAMA_MODEL = "llama3.2:3b"
DEFAULT_OLLAMA_QUICK = "llama3.2:1b"


@dataclass(frozen=True)
class LlmRoute:
    provider: str
    api_key: str
    base_url: str
    model: str
    deep_think_model: str
    quick_think_model: str
    label: str


def _env_bool(name: str, default: bool = True) -> bool:
    raw = (os.getenv(name) or "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on", "auto")


def _ollama_reachable(host: str, timeout: float = 2.0) -> bool:
    try:
        import requests

        return bool(requests.get(f"{host.rstrip('/')}/api/tags", timeout=timeout).ok)
    except Exception:
        return False


def _key(settings: Settings | None, attr: str, env_name: str) -> str:
    if settings is not None:
        val = getattr(settings, attr, None)
        if val:
            return str(val).strip()
    return (os.getenv(env_name) or "").strip()


def resolve_llm_route(
    settings: Settings | None = None,
    *,
    env_only: bool = False,
) -> LlmRoute | None:
    """Pick the best available LLM backend for unattended autopilot."""
    if settings is None and not env_only:
        try:
            from apex.core.config import get_settings

            settings = get_settings()
        except Exception:
            settings = None

    if settings is not None and not _env_bool("LLM_AUTO_ROUTING", True):
        return _route_from_explicit_settings(settings)

    if not _env_bool("LLM_AUTO_ROUTING", True):
        return None

    groq_key = _key(settings, "groq_api_key", "GROQ_API_KEY")
    if groq_key:
        return LlmRoute(
            provider="groq",
            api_key=groq_key,
            base_url="https://api.groq.com/openai/v1",
            model=os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL),
            deep_think_model=os.getenv("LLM_DEEP_THINK_MODEL", os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL)),
            quick_think_model=os.getenv("LLM_QUICK_THINK_MODEL", os.getenv("GROQ_QUICK_MODEL", DEFAULT_GROQ_QUICK)),
            label="groq",
        )

    gemini_key = _key(settings, "gemini_api_key", "GEMINI_API_KEY") or (
        os.getenv("GOOGLE_API_KEY") or ""
    ).strip()
    if gemini_key:
        return LlmRoute(
            provider="openai",
            api_key=gemini_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            model=os.getenv("GEMINI_MODEL", os.getenv("LLM_MODEL", DEFAULT_GEMINI_MODEL)),
            deep_think_model=os.getenv("LLM_DEEP_THINK_MODEL", os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)),
            quick_think_model=os.getenv("LLM_QUICK_THINK_MODEL", os.getenv("GEMINI_QUICK_MODEL", DEFAULT_GEMINI_MODEL)),
            label="gemini",
        )

    openrouter_key = _key(settings, "openrouter_key", "OPENROUTER_KEY")
    if openrouter_key:
        return LlmRoute(
            provider="openai",
            api_key=openrouter_key,
            base_url="https://openrouter.ai/api/v1",
            model=os.getenv("OPENROUTER_MODEL", os.getenv("LLM_MODEL", DEFAULT_OPENROUTER_MODEL)),
            deep_think_model=os.getenv(
                "LLM_DEEP_THINK_MODEL",
                os.getenv("OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODEL),
            ),
            quick_think_model=os.getenv(
                "LLM_QUICK_THINK_MODEL",
                os.getenv("OPENROUTER_QUICK_MODEL", DEFAULT_OPENROUTER_MODEL),
            ),
            label="openrouter",
        )

    host = (
        (settings.ollama_host if settings else None)
        or os.getenv("OLLAMA_HOST", "http://localhost:11434")
    ).rstrip("/")
    if _ollama_reachable(host):
        ollama_default = settings.ollama_model if settings else DEFAULT_OLLAMA_MODEL
        model = os.getenv("OLLAMA_MODEL", ollama_default)
        quick = os.getenv("LLM_QUICK_THINK_MODEL", DEFAULT_OLLAMA_QUICK)
        return LlmRoute(
            provider="ollama",
            api_key="ollama",
            base_url=f"{host}/v1",
            model=model,
            deep_think_model=os.getenv("LLM_DEEP_THINK_MODEL", model),
            quick_think_model=quick,
            label="ollama",
        )

    LOGGER.warning(
        "No LLM route available: set GROQ_API_KEY, GEMINI_API_KEY, OPENROUTER_KEY, or run Ollama"
    )
    return None


def _route_from_explicit_settings(settings: Settings) -> LlmRoute | None:
    prov = (settings.llm_provider or "ollama").lower()
    if prov == "groq":
        key = (settings.groq_api_key or os.getenv("GROQ_API_KEY") or "").strip()
        if not key:
            return None
        return LlmRoute(
            provider="groq",
            api_key=key,
            base_url=settings.llm_backend_url or "https://api.groq.com/openai/v1",
            model=settings.llm_model,
            deep_think_model=settings.llm_deep_think_model,
            quick_think_model=settings.llm_quick_think_model,
            label="groq",
        )
    if prov == "ollama":
        host = settings.ollama_host.rstrip("/")
        return LlmRoute(
            provider="ollama",
            api_key="ollama",
            base_url=f"{host}/v1",
            model=settings.llm_model,
            deep_think_model=settings.llm_deep_think_model,
            quick_think_model=settings.llm_quick_think_model,
            label="ollama",
        )
    key = os.getenv("OPENAI_API_KEY", "") or (settings.openrouter_key or "")
    base = settings.llm_backend_url or "https://api.openai.com/v1"
    if prov in ("openrouter", "openai") and (settings.openrouter_key or "").strip():
        key = settings.openrouter_key or key
        base = "https://openrouter.ai/api/v1"
    return LlmRoute(
        provider="openai",
        api_key=key or "ollama",
        base_url=base,
        model=settings.llm_model,
        deep_think_model=settings.llm_deep_think_model,
        quick_think_model=settings.llm_quick_think_model,
        label=prov,
    )


def apply_llm_route_to_environ(route: LlmRoute) -> None:
    """Publish resolved route so pydantic Settings and adapters agree."""
    os.environ["LLM_PROVIDER"] = route.provider
    os.environ["LLM_BACKEND_URL"] = route.base_url
    os.environ["LLM_MODEL"] = route.model
    os.environ["LLM_DEEP_THINK_MODEL"] = route.deep_think_model
    os.environ["LLM_QUICK_THINK_MODEL"] = route.quick_think_model
    os.environ["APEX_LLM_ROUTE"] = route.label
    if route.provider == "groq":
        os.environ.setdefault("GROQ_API_KEY", route.api_key)
    elif route.label == "gemini":
        os.environ.setdefault("GEMINI_API_KEY", route.api_key)
    elif route.label == "openrouter":
        os.environ.setdefault("OPENROUTER_KEY", route.api_key)
    LOGGER.info(
        "LLM auto-route: %s model=%s deep=%s quick=%s",
        route.label,
        route.model,
        route.deep_think_model,
        route.quick_think_model,
    )


def bootstrap_llm_routing() -> LlmRoute | None:
    """Resolve from os.environ only (safe during Settings module load)."""
    route = resolve_llm_route(settings=None, env_only=True)
    if route is not None:
        apply_llm_route_to_environ(route)
    return route
