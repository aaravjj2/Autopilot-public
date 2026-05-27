"""Paths, env loading, HTTP helpers for WC2026 autopilot."""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import time
from functools import wraps
from pathlib import Path
from typing import Any, Callable, TypeVar

import requests
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
AUTOPILOT_ROOT = PROJECT_ROOT.parent
SRC_ROOT = PROJECT_ROOT / "src"
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_DB = PROJECT_ROOT / "data" / "db"
DEFAULT_DB_PATH = DATA_DB / "wc2026.sqlite"

T = TypeVar("T")
_ENV_LOADED = False
_CACHE: dict[str, tuple[float, Any]] = {}


def bootstrap_env() -> None:
    """Load parent Autopilot keys.env + .env, then local .env."""
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    keys = AUTOPILOT_ROOT / "keys.env"
    root_env = AUTOPILOT_ROOT / ".env"
    local_env = PROJECT_ROOT / ".env"
    if keys.is_file():
        load_dotenv(keys, override=False)
    if root_env.is_file():
        load_dotenv(root_env, override=True)
    if local_env.is_file():
        load_dotenv(local_env, override=True)
    _ENV_LOADED = True


def get_logger(name: str) -> logging.Logger:
    bootstrap_env()
    level = (os.getenv("LOG_LEVEL") or "INFO").upper()
    logging.basicConfig(level=getattr(logging, level, logging.INFO))
    return logging.getLogger(name)


def db_path() -> Path:
    bootstrap_env()
    raw = (os.getenv("WC_DB_PATH") or "").strip()
    return Path(raw) if raw else DEFAULT_DB_PATH


def get_db_connection(path: Path | None = None) -> sqlite3.Connection:
    p = path or db_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p))
    conn.row_factory = sqlite3.Row
    return conn


def download_text(url: str, *, dest_name: str | None = None, timeout: float = 60.0) -> str:
    """Download URL with optional cache under data/raw."""
    DATA_RAW.mkdir(parents=True, exist_ok=True)
    if dest_name:
        cache = DATA_RAW / dest_name
        if cache.is_file() and cache.stat().st_size > 0:
            return cache.read_text(encoding="utf-8", errors="replace")
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    text = resp.text
    if dest_name:
        (DATA_RAW / dest_name).write_text(text, encoding="utf-8")
    return text


def download_bytes(url: str, *, dest_name: str | None = None, timeout: float = 120.0) -> bytes:
    DATA_RAW.mkdir(parents=True, exist_ok=True)
    if dest_name:
        cache = DATA_RAW / dest_name
        if cache.is_file() and cache.stat().st_size > 0:
            return cache.read_bytes()
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    data = resp.content
    if dest_name:
        (DATA_RAW / dest_name).write_bytes(data)
    return data


def ttl_cache(seconds: float) -> Callable[[Callable[..., T]], Callable[..., T]]:
    def decorator(fn: Callable[..., T]) -> Callable[..., T]:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            key = f"{fn.__module__}.{fn.__name__}:{json.dumps([args, kwargs], default=str)}"
            now = time.time()
            hit = _CACHE.get(key)
            if hit and now - hit[0] < seconds:
                return hit[1]
            result = fn(*args, **kwargs)
            _CACHE[key] = (now, result)
            return result

        return wrapper

    return decorator


def clear_cache() -> None:
    _CACHE.clear()
