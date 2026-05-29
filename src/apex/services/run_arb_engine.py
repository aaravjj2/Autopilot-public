from __future__ import annotations

import logging

from apex.core.config import get_settings
from apex.repositories.sqlite_store import SQLiteStore
from apex.services.arb_scan import scan_and_persist

LOGGER = logging.getLogger(__name__)


def main() -> None:
    settings = get_settings()
    store = SQLiteStore(settings.sqlite_path)
    found = scan_and_persist(store, limit=100)
    LOGGER.info("Detected %d arb opportunities", len(found))


if __name__ == "__main__":
    main()
