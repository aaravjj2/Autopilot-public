"""Load repo-level keys.env + .env and normalize Alpaca variable names."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BOOTSTRAPPED = False


def repo_root() -> Path:
    return _REPO_ROOT


def bootstrap_environment(*, force: bool = False) -> Path:
    """Load keys.env then .env; map APCA_* aliases for Alpaca paper."""
    global _BOOTSTRAPPED
    if _BOOTSTRAPPED and not force:
        return _REPO_ROOT

    keys_file = _REPO_ROOT / "keys.env"
    env_file = _REPO_ROOT / ".env"
    if keys_file.is_file():
        load_dotenv(keys_file, override=False)
    if env_file.is_file():
        load_dotenv(env_file, override=True)

    aliases = (
        ("ALPACA_API_KEY", "APCA_API_KEY_ID"),
        ("ALPACA_SECRET_KEY", "APCA_API_SECRET_KEY"),
        ("ALPACA_BASE_URL", "APCA_ENDPOINT"),
        ("ALPACA_DATA_URL", "ALPACA_DATA_URL"),
        ("KALSHI_API_KEY", "KALSHI_ACCESS_KEY"),
        ("KALSHI_API_KEY", "KALSHI_API_KEY_ID"),
        ("KALSHI_API_PRIVATE_KEY", "KALSHI_PRIVATE_KEY"),
    )
    for target, source in aliases:
        if not (os.getenv(target) or "").strip() and (os.getenv(source) or "").strip():
            os.environ[target] = os.environ[source]

    pem = (os.getenv("KALSHI_API_PRIVATE_KEY") or "").strip()
    if not pem or "BEGIN" not in pem:
        key_path = (os.getenv("KALSHI_PRIVATE_KEY_PATH") or "").strip()
        if key_path:
            pem_file = Path(key_path)
            if not pem_file.is_absolute():
                pem_file = _REPO_ROOT / pem_file
            if pem_file.is_file():
                os.environ["KALSHI_API_PRIVATE_KEY"] = pem_file.read_text(encoding="utf-8")

    key = (os.getenv("KALSHI_API_KEY") or "").strip()
    pem = (os.getenv("KALSHI_API_PRIVATE_KEY") or "").strip()
    if key and pem and "BEGIN" in pem:
        if not (os.getenv("KALSHI_BASE_URL") or "").strip():
            os.environ["KALSHI_BASE_URL"] = "https://demo-api.kalshi.co/trade-api/v2"
        demo_flag = (os.getenv("KALSHI_DEMO_TRADING_ENABLED") or "").strip().lower()
        if demo_flag in ("", "auto"):
            os.environ["KALSHI_DEMO_TRADING_ENABLED"] = "true"

    for loop_var, default in (
        ("APEX_PM_AGENTS_LOOP", "true"),
        ("APEX_ARB_SCAN_LOOP", "true"),
        ("APEX_EQUITY_LOOP", "true"),
        ("APEX_SELF_IMPROVEMENT_LOOP", "true"),
        ("APEX_MORNING_CHAIN", "true"),
    ):
        if not (os.getenv(loop_var) or "").strip():
            os.environ[loop_var] = default

    if not (os.getenv("SHOWCASE_MODE") or "").strip():
        os.environ["SHOWCASE_MODE"] = "false"

    if not (os.getenv("ALPACA_PAPER_TRADE") or "").strip():
        os.environ["ALPACA_PAPER_TRADE"] = "true"

    from apex.core.llm_routing import bootstrap_llm_routing

    bootstrap_llm_routing()

    _BOOTSTRAPPED = True
    return _REPO_ROOT


def env_file_paths() -> tuple[str, ...]:
    """Pydantic-settings env_file tuple: keys first, .env overrides."""
    bootstrap_environment()
    paths: list[str] = []
    keys_file = _REPO_ROOT / "keys.env"
    env_file = _REPO_ROOT / ".env"
    if keys_file.is_file():
        paths.append(str(keys_file))
    if env_file.is_file():
        paths.append(str(env_file))
    return tuple(paths) if paths else (str(env_file),)
