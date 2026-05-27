from __future__ import annotations

from apex.core.config import get_settings
from apex.repositories.sqlite_store import SQLiteStore
from apex.services.arb_scan import scan_and_persist


def main() -> None:
    settings = get_settings()
    store = SQLiteStore(settings.sqlite_path)
    found = scan_and_persist(store, limit=100)
    print(f"Detected {len(found)} arb opportunities")


if __name__ == "__main__":
    main()
