"""Verify Prometheus counters increment on hot paths."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from apex.domain.models import ArbOpportunity


def test_arb_edge_gauge_set_on_scan(tmp_path):
    """APEX_ARB_EDGE.set() is called after a successful scan."""
    from apex.core.config import Settings
    from apex.repositories.sqlite_store import SQLiteStore

    fake_opp = ArbOpportunity(
        kalshi_ticker="KX-TEST",
        poly_market_id="poly-test",
        question="Test?",
        kalshi_title="Test?",
        poly_title="Test?",
        kalshi_yes_ask=0.48,
        poly_no_ask=0.47,
        gross_spread=0.05,
        net_edge=0.03,
        settlement_match_score=0.9,
        settlement_flags=[],
        volume_kalshi=50000,
        volume_poly=50000,
        kelly_fraction=0.3,
    )

    settings = Settings(sqlite_path=tmp_path / "test.db", demo_mode=True)
    store = SQLiteStore(settings.sqlite_path)

    with patch("apex.services.arb_scan.ArbEngine") as MockEngine:
        MockEngine.return_value.scan.return_value = [fake_opp]
        gauge_mock = MagicMock()
        with patch("apex.observability.prometheus_metrics.APEX_ARB_EDGE", gauge_mock):
            from apex.services.arb_scan import scan_and_persist

            scan_and_persist(store, settings=settings)
            gauge_mock.set.assert_called_once_with(0.03)


def test_metrics_endpoint_returns_bytes():
    """GET /metrics returns prometheus text format."""
    from apex.observability.prometheus_metrics import metrics_payload

    result = metrics_payload()
    assert isinstance(result, bytes)
