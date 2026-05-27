"""Shared pytest configuration."""

from __future__ import annotations

import pytest


def pytest_collection_modifyitems(config, items):
    for item in items:
        path = str(item.fspath)
        if "test_arb_engine" in path or "test_week7" in path and "502" in path:
            item.add_marker(pytest.mark.slow)
