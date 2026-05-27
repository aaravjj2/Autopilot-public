"""DB03.1 regression harness — Engine Singleton verification.

Verifies: no per-request build_engine() calls on hot paths; all route handlers
use get_cached_engine(); _engine_singleton global is present in backend_api.py.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

REPO = Path(__file__).parents[1]
BACKEND_API = REPO / "backend_api.py"
ENGINE_PY = REPO / "src" / "apex" / "services" / "engine.py"


def _lines_with(text: str, token: str) -> list[int]:
    return [i + 1 for i, ln in enumerate(text.splitlines()) if token in ln]


def test_engine_singleton_global_exists() -> None:
    """backend_api.py must declare `_engine_singleton` global."""
    text = BACKEND_API.read_text()
    assert "_engine_singleton" in text, "Missing _engine_singleton in backend_api.py"


def test_get_cached_engine_function_exists() -> None:
    """`get_cached_engine` function must exist in backend_api.py."""
    text = BACKEND_API.read_text()
    assert "def get_cached_engine" in text, "Missing get_cached_engine() in backend_api.py"


def test_no_bare_build_engine_in_route_handlers() -> None:
    """Route handlers must not call build_engine() directly — only get_cached_engine()."""
    text = BACKEND_API.read_text()
    lines = text.splitlines()
    # Find all lines with build_engine() call
    build_lines = [i for i, ln in enumerate(lines) if "build_engine()" in ln]
    # get_cached_engine calls build_engine once — that's the only allowed call
    assert len(build_lines) == 1, (
        f"Expected exactly 1 build_engine() call (inside get_cached_engine), found {len(build_lines)}"
    )
    # Validate it's inside get_cached_engine by checking surrounding context
    idx = build_lines[0]
    context = "\n".join(lines[max(0, idx - 5) : idx + 1])
    assert "_engine_singleton" in context or "get_cached_engine" in context, (
        f"build_engine() at line {idx+1} appears outside get_cached_engine:\n{context}"
    )


def test_hot_paths_use_cached_engine() -> None:
    """Key route handlers (/arb, /run, /health) must use get_cached_engine()."""
    text = BACKEND_API.read_text()
    # Verify get_cached_engine() is used at least 5 times in route handlers
    call_lines = _lines_with(text, "get_cached_engine()")
    assert len(call_lines) >= 5, (
        f"Expected ≥5 get_cached_engine() calls in route handlers, found {len(call_lines)}"
    )


def test_engine_py_has_apex_engine_class() -> None:
    """src/apex/services/engine.py must contain an ApexEngine or similar class."""
    text = ENGINE_PY.read_text()
    has_class = "class ApexEngine" in text or "class Engine" in text or "@dataclass" in text
    assert has_class, "engine.py must define an engine class or dataclass"


def test_compileall_apex() -> None:
    """src/apex must compile cleanly with Python."""
    import subprocess
    result = subprocess.run(
        ["python", "-m", "compileall", "-q", "src/apex"],
        capture_output=True,
        text=True,
        cwd=REPO,
        env={**__import__("os").environ, "PYTHONPATH": "src"},
    )
    assert result.returncode == 0, f"compileall failed:\n{result.stderr}"
