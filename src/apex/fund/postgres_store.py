"""PostgreSQL multi-tenant stub (Phase 5 backlog)."""

from __future__ import annotations

from apex.core.config import Settings


def postgres_enabled(settings: Settings | None = None) -> bool:
    from apex.core.config import get_settings

    s = settings or get_settings()
    return bool((s.postgres_url or "").strip())


def tenant_dsn(settings: Settings | None = None) -> str:
    from apex.core.config import get_settings

    return (settings or get_settings()).postgres_url or ""
