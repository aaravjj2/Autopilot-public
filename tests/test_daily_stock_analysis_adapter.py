from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from apex.core.config import Settings
from apex.integrations.daily_stock_analysis_adapter import DailyStockAnalysisAdapter


@pytest.fixture
def dsa_repo(tmp_path: Path) -> Path:
    root = tmp_path / "dsa"
    root.mkdir()
    (root / "main.py").write_text("# stub\n", encoding="utf-8")
    reports = root / "reports"
    reports.mkdir()
    (reports / "market_review_20260518.md").write_text(
        "US equities bullish tone; risk-on breadth.",
        encoding="utf-8",
    )
    return root


def test_adapter_reads_market_review_from_reports(dsa_repo: Path) -> None:
    settings = Settings(
        daily_stock_analysis_repo_path=str(dsa_repo),
        daily_stock_analysis_enabled=True,
        daily_stock_analysis_market_review=True,
        daily_stock_analysis_stock_digest=False,
    )
    adapter = DailyStockAnalysisAdapter(str(dsa_repo), settings=settings)
    assert adapter.available

    with patch.object(adapter, "_run_main", return_value=MagicMock(returncode=0, stdout="", stderr="")):
        report = adapter.get_daily_market_report(symbols=["AAPL", "MSFT"])

    assert report["source"] == "daily_stock_analysis"
    assert "bullish" in report["raw_report"].lower()
    assert report["regime"] == "risk_on"


def test_adapter_unavailable_without_repo(tmp_path: Path) -> None:
    adapter = DailyStockAnalysisAdapter(str(tmp_path / "missing"), settings=Settings())
    assert not adapter.available
    out = adapter.get_daily_market_report()
    assert out["source"] == "daily_stock_analysis_unavailable"
