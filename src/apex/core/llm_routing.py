"""Automatic LLM provider selection: Groq → Ollama → OpenRouter → Gemini (opt-in)."""

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


def _gemini_enabled() -> bool:
    """Gemini is opt-in; disabled by default to avoid quota/auth churn."""
    return _env_bool("LLM_ENABLE_GEMINI", False)


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


def _route_groq(settings: Settings | None) -> LlmRoute | None:
    groq_key = _key(settings, "groq_api_key", "GROQ_API_KEY")
    if not groq_key:
        return None
    # Quick health check: verify key isn't revoked/restricted
    _groq_key_revoked = os.getenv("_GROQ_KEY_REVOKED", "").strip().lower() in ("1", "true")
    if _groq_key_revoked:
        LOGGER.warning("Skipping groq — key previously detected as revoked/restricted")
        return None
    return LlmRoute(
        provider="groq",
        api_key=groq_key,
        base_url="https://api.groq.com/openai/v1",
        model=os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL),
        deep_think_model=os.getenv("LLM_DEEP_THINK_MODEL", os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL)),
        quick_think_model=os.getenv("LLM_QUICK_THINK_MODEL", os.getenv("GROQ_QUICK_MODEL", DEFAULT_GROQ_QUICK)),
        label="groq",
    )


def _route_gemini(settings: Settings | None) -> LlmRoute | None:
    if not _gemini_enabled():
        return None
    gemini_key = _key(settings, "gemini_api_key", "GEMINI_API_KEY") or (
        os.getenv("GOOGLE_API_KEY") or ""
    ).strip()
    if not gemini_key:
        return None
    return LlmRoute(
        provider="openai",
        api_key=gemini_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        model=os.getenv("GEMINI_MODEL", os.getenv("LLM_MODEL", DEFAULT_GEMINI_MODEL)),
        deep_think_model=os.getenv("LLM_DEEP_THINK_MODEL", os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)),
        quick_think_model=os.getenv("LLM_QUICK_THINK_MODEL", os.getenv("GEMINI_QUICK_MODEL", DEFAULT_GEMINI_MODEL)),
        label="gemini",
    )


def _route_openrouter(settings: Settings | None) -> LlmRoute | None:
    openrouter_key = _key(settings, "openrouter_key", "OPENROUTER_KEY")
    if not openrouter_key:
        return None
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


def _route_ollama(settings: Settings | None) -> LlmRoute | None:
    host = (
        (settings.ollama_host if settings else None)
        or os.getenv("OLLAMA_HOST", "http://localhost:11434")
    ).rstrip("/")
    if not _ollama_reachable(host):
        return None
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


def _route_openai(settings: Settings | None) -> LlmRoute | None:
    """Fallback route using OPENAI_API_KEY + optional OPENAI_BASE_URL."""
    api_key = _key(settings, "openai_api_key", "OPENAI_API_KEY")
    if not api_key:
        return None
    base_url = (
        (settings.llm_backend_url if settings else "") or
        os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    ).rstrip("/")
    model = os.getenv("LLM_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    return LlmRoute(
        provider="openai",
        api_key=api_key,
        base_url=base_url,
        model=model,
        deep_think_model=os.getenv("LLM_DEEP_THINK_MODEL", model),
        quick_think_model=os.getenv("LLM_QUICK_THINK_MODEL", "gpt-4o-mini"),
        label="openai-fallback",
    )


def resolve_llm_routes(
    settings: Settings | None = None,
    *,
    env_only: bool = False,
) -> list[LlmRoute]:
    """Return all usable LLM backends in priority order (for runtime fallback)."""
    if settings is None and not env_only:
        try:
            from apex.core.config import get_settings

            settings = get_settings()
        except Exception:
            settings = None

    if settings is not None and not _env_bool("LLM_AUTO_ROUTING", True):
        single = _route_from_explicit_settings(settings)
        return [single] if single is not None else []

    if not _env_bool("LLM_AUTO_ROUTING", True):
        return []

    prefer = (os.getenv("LLM_ROUTE_PREFERENCE") or "").strip().lower()
    builders: list[tuple[str, object]] = [
        ("groq", _route_groq),
        ("ollama", _route_ollama),
        ("openrouter", _route_openrouter),
        ("gemini", _route_gemini),
        ("openai-fallback", _route_openai),
    ]
    if prefer == "ollama":
        builders.sort(key=lambda x: 0 if x[0] == "ollama" else 1)
    elif prefer == "groq":
        builders.sort(key=lambda x: 0 if x[0] == "groq" else 1)
    elif prefer == "gemini" and _gemini_enabled():
        builders.sort(key=lambda x: 0 if x[0] == "gemini" else 1)

    routes: list[LlmRoute] = []
    seen: set[str] = set()
    for _name, builder in builders:
        route = builder(settings)
        if route is None or route.label in seen:
            continue
        routes.append(route)
        seen.add(route.label)

    if not routes:
        LOGGER.warning(
            "No LLM route available: set GROQ_API_KEY, run Ollama, OPENROUTER_KEY, "
            "or enable LLM_ENABLE_GEMINI — autopilot will use heuristic/scripts mode"
        )
    return routes


def resolve_llm_route(
    settings: Settings | None = None,
    *,
    env_only: bool = False,
) -> LlmRoute | None:
    """Pick the best available LLM backend for unattended autopilot."""
    routes = resolve_llm_routes(settings, env_only=env_only)
    return routes[0] if routes else None


def openai_client_from_route(route: LlmRoute) -> object | None:
    """Build an OpenAI-compatible client for a resolved route."""
    if route.provider == "ollama":
        pass
    elif not route.api_key.strip():
        return None
    if not route.base_url.strip():
        return None
    try:
        from openai import OpenAI  # type: ignore[import-untyped]

        return OpenAI(api_key=route.api_key, base_url=route.base_url)
    except ImportError:
        LOGGER.warning("openai package not installed; run `pip install openai`")
        return None
    except Exception as exc:
        LOGGER.warning("LLM client init failed for %s: %s", route.label, exc)
        return None


def llm_error_disables_route(exc: BaseException) -> bool:
    """True when a failed call should stop retrying this provider."""
    msg = str(exc).lower()
    if "429" in msg or "resource_exhausted" in msg:
        return False
    tokens = (
        "401",
        "403",
        "invalid api key",
        "api_key",
        "permission_denied",
        "organization_restricted",
        "organization has been restricted",
        "authentication",
    )
    is_fatal = any(token in msg for token in tokens)
    if is_fatal and "organization_restricted" in msg:
        os.environ["_GROQ_KEY_REVOKED"] = "true"
        LOGGER.warning("Groq key marked as revoked — subsequent routes will skip groq")
    return is_fatal


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
