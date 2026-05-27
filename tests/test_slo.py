from __future__ import annotations

from datetime import datetime

from apex.dashboard.slo import ET, build_pipeline_slo_rows


def test_slo_stale_after_deadline_for_failed_job() -> None:
    today = "2026-05-13"
    fake_now = datetime(2026, 5, 13, 22, 0, tzinfo=ET)
    jobs = [{"job_name": "market_snapshot", "status": "failed", "run_date": today}]
    rows = build_pipeline_slo_rows(jobs, fake_now)
    ms = next(r for r in rows if r.job_name == "market_snapshot")
    assert ms.stale is True


def test_slo_not_stale_when_success() -> None:
    today = "2026-05-13"
    fake_now = datetime(2026, 5, 13, 22, 0, tzinfo=ET)
    jobs = [{"job_name": "market_snapshot", "status": "success", "run_date": today}]
    rows = build_pipeline_slo_rows(jobs, fake_now)
    ms = next(r for r in rows if r.job_name == "market_snapshot")
    assert ms.stale is False
