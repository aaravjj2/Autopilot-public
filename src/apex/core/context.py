from __future__ import annotations

import contextvars
from typing import Any

_run_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("apex_run_id", default=None)


def get_run_id() -> str | None:
    return _run_id.get()


def set_run_id(run_id: str) -> contextvars.Token[str | None]:
    return _run_id.set(run_id)


def reset_run_id(token: contextvars.Token[str | None]) -> None:
    _run_id.reset(token)
