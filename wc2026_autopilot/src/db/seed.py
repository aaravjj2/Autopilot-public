"""Load historical + fixture data into SQLite."""

from __future__ import annotations

import sqlite3

from config import get_db_connection, get_logger
from db.schema import init_db
from ingestion import worldcup_history
from ingestion.wc2026_fixtures import fetch_and_insert_fixtures

LOGGER = get_logger(__name__)


def seed_all(conn: sqlite3.Connection | None = None) -> dict[str, int]:
    own = conn is None
    db = conn or get_db_connection()
    init_db(db)
    counts = worldcup_history.load_all(db)
    counts["fixtures_2026"] = fetch_and_insert_fixtures(db)
    LOGGER.info("Seed complete: %s", counts)
    if own:
        db.close()
    return counts
