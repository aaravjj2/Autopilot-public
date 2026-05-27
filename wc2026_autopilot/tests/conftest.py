import os
import sqlite3

import pytest


@pytest.fixture(scope="session")
def db_path(tmp_path_factory):
    return tmp_path_factory.mktemp("db") / "test.sqlite"


@pytest.fixture(autouse=True)
def _env(db_path, monkeypatch):
    monkeypatch.setenv("WC_DB_PATH", str(db_path))
    monkeypatch.setenv("MIN_MARKET_VOLUME", "1000")
    monkeypatch.setenv("MAX_KELLY_FRACTION", "0.05")


def live_enabled() -> bool:
    return os.getenv("WC_SKIP_LIVE", "0") != "1"


def require_live():
    if not live_enabled():
        pytest.skip("WC_SKIP_LIVE=1")

def pytest_collection_modifyitems(config, items):
    if live_enabled():
        return
    skip_live = pytest.mark.skip(reason="WC_SKIP_LIVE=1")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip_live)


@pytest.fixture(scope="session")
def db(db_path):
    """Session-scoped seeded DB connection for read-heavy tests."""
    from db.seed import seed_all
    from db.schema import init_db

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    init_db(conn)
    seed_all(conn)
    yield conn
    conn.close()


@pytest.fixture
def empty_db(tmp_path):
    """Fresh empty DB connection for write tests."""
    from db.schema import init_db

    p = tmp_path / "empty.sqlite"
    conn = sqlite3.connect(str(p))
    conn.row_factory = sqlite3.Row
    init_db(conn)
    yield conn
    conn.close()
