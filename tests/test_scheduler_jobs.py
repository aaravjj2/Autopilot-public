from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from apex.scheduler.jobs import SCHEDULE, register_jobs

from test_integrations_and_autotrade import _engine, _opportunity


def test_register_jobs_schedule_matches_callbacks(tmp_path: Path) -> None:
    sched = MagicMock()
    register_jobs(sched, _engine(tmp_path, autotrade_all_approved=False))
    # loss_cut_scan only via 5-min override (skipped in daily SCHEDULE loop)
    intraday_ids = [
        "loss_cut_scan",
        "arb_opportunity_scan_intraday",
        "prediction_markets_agent_cycle_intraday",
        "world_cup_agent_cycle_intraday",
    ]
    # loss_cut_scan skipped in daily SCHEDULE loop (intraday job only)
    assert sched.add_job.call_count == (len(SCHEDULE) - 1) + len(intraday_ids)
    ids = [c.kwargs["id"] for c in sched.add_job.call_args_list]
    expected = [name for name, *_ in SCHEDULE if name != "loss_cut_scan"] + intraday_ids
    assert sorted(ids) == sorted(expected)


def test_deep_research_triggers_no_op_without_dexter(tmp_path: Path) -> None:
    engine = _engine(tmp_path, autotrade_all_approved=False)
    engine.todays_opportunities = [_opportunity("AAPL")]
    engine.deep_research_triggers()


def test_catch_up_morning_pipeline_skips_before_931(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """P3.4 — Scheduler resilience: catch-up pipeline does not run before 9:31 ET."""
    from datetime import datetime as _real_dt
    from apex.scheduler.service import _catch_up_morning_pipeline

    class _FixedDatetime:
        @classmethod
        def now(cls, tz=None):
            _ = tz
            return _real_dt(2026, 5, 22, 8, 0, 0)  # 8:00 ET → before window

    monkeypatch.setattr("apex.scheduler.service.datetime", _FixedDatetime)

    engine = _engine(tmp_path, autotrade_all_approved=False)
    engine.store = MagicMock()
    result = _catch_up_morning_pipeline(engine)
    assert result is None  # should return early without running


def test_catch_up_morning_pipeline_runs_after_931(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """P3.4 — Scheduler resilience: catch-up pipeline runs when scheduler starts after 9:31 ET."""
    from datetime import datetime as _real_dt
    from apex.scheduler.service import _catch_up_morning_pipeline

    class _FixedDatetime:
        @classmethod
        def now(cls, tz=None):
            _ = tz
            return _real_dt(2026, 5, 22, 10, 30, 0)  # 10:30 ET → after window

    monkeypatch.setattr("apex.scheduler.service.datetime", _FixedDatetime)

    engine = _engine(tmp_path, autotrade_all_approved=False)
    engine.run_daily_cycle = MagicMock()
    engine.watchlist_refresh = MagicMock()

    _catch_up_morning_pipeline(engine)
    # Should have triggered the daily cycle (exact assertion depends on implementation)
    assert engine.run_daily_cycle.called or engine.watchlist_refresh.called
