#!/usr/bin/env python3
"""Seed SQLite with hackathon demo arb opportunities and audit events."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ALPACA_PAPER_TRADE", "true")

from apex.core.config import get_settings
from apex.core.env_bootstrap import bootstrap_environment
from apex.demo.seed_data import seed_demo_database
from apex.repositories.sqlite_store import SQLiteStore


def main() -> None:
    bootstrap_environment(force=True)
    settings = get_settings()
    store = SQLiteStore(settings.sqlite_path)
    stats = seed_demo_database(store)
    print(f"Demo seed OK: {stats} -> {settings.sqlite_path}")


if __name__ == "__main__":
    main()
