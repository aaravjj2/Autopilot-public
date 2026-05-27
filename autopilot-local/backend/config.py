from __future__ import annotations

import os
import sys
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

# Repo root: Autopilot/ (parent of autopilot-local/)
REPO_ROOT = Path(__file__).resolve().parents[2]
LOCAL_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))


def bootstrap_copy_trading_env() -> None:
    """Share keys with APEX: keys.env → .env → .env.local."""
    keys_file = REPO_ROOT / "keys.env"
    apex_env = REPO_ROOT / ".env"
    local_env = LOCAL_ROOT / ".env.local"
    if keys_file.is_file():
        load_dotenv(keys_file, override=False)
    if apex_env.is_file():
        load_dotenv(apex_env, override=True)
    if local_env.is_file():
        load_dotenv(local_env, override=True)

    aliases = (
        ("ALPACA_API_KEY", "APCA_API_KEY_ID"),
        ("ALPACA_API_SECRET", "APCA_API_SECRET_KEY"),
        ("ALPACA_API_SECRET", "ALPACA_SECRET_KEY"),
        ("ALPACA_BASE_URL", "APCA_ENDPOINT"),
    )
    for target, source in aliases:
        if not (os.getenv(target) or "").strip() and (os.getenv(source) or "").strip():
            os.environ[target] = os.environ[source]
    if not (os.getenv("ALPACA_API_SECRET") or "").strip() and (
        os.getenv("ALPACA_SECRET_KEY") or ""
    ).strip():
        os.environ["ALPACA_API_SECRET"] = os.environ["ALPACA_SECRET_KEY"]


@lru_cache(maxsize=1)
def get_settings() -> dict[str, str]:
    bootstrap_copy_trading_env()
    db_default = str(LOCAL_ROOT / "autopilot.db")
    return {
        "alpaca_api_key": os.getenv("ALPACA_API_KEY", os.getenv("APCA_API_KEY_ID", "")),
        "alpaca_api_secret": os.getenv(
            "ALPACA_API_SECRET",
            os.getenv("ALPACA_SECRET_KEY", os.getenv("APCA_API_SECRET_KEY", "")),
        ),
        "alpaca_base_url": os.getenv(
            "ALPACA_BASE_URL",
            os.getenv("APCA_ENDPOINT", "https://paper-api.alpaca.markets"),
        ),
        "alpaca_data_url": os.getenv(
            "ALPACA_DATA_URL", "https://data.alpaca.markets"
        ),
        "quiver_api_key": os.getenv("QUIVER_API_KEY", ""),
        "sec_api_key": os.getenv("SEC_API_KEY", ""),
        "db_path": os.getenv("AUTOPILOT_DB_PATH", db_default),
        "paper_allocation_usd": os.getenv("PAPER_ALLOCATION_USD", "100000"),
    }
