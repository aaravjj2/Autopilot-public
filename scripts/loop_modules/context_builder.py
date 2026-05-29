from __future__ import annotations

import json
import subprocess
from pathlib import Path

import httpx

from loop_modules.gcloud_deployer import read_cloud_run_url, verify_cloud_health
from loop_modules.models import LoopContext, LoopState

WORKSPACE = Path("/home/aarav/Aarav/Autopilot")


def _git_changed_files() -> list[str]:
    try:
        git_status_out = subprocess.check_output(
            ["git", "status", "--short"],
            text=True,
            cwd=WORKSPACE,
        )
        return [line.split()[-1] for line in git_status_out.strip().split("\n") if line.strip()]
    except Exception:
        return []


def _last_test_report(iteration: int) -> dict[str, object]:
    if iteration <= 1:
        return {}
    log_path = WORKSPACE / "data" / "loop_logs" / f"iteration_{iteration - 1:04d}_tests.json"
    if not log_path.exists():
        return {}
    try:
        with open(log_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _failure_messages(report: dict[str, object]) -> list[str]:
    failures: list[str] = []
    if not report:
        return failures
    if report.get("overall_passed") is True:
        return failures
    if int(report.get("pytest_failed") or 0) > 0:
        failures.append(f"pytest_failed={report.get('pytest_failed')}")
    if report.get("api_smoke_passed") is False:
        failures.append("api_smoke_failed")
    if report.get("cloud_smoke_passed") is False:
        failures.append("cloud_smoke_failed")
    if report.get("tsc_passed") is False:
        failures.append("tsc_failed")
    if int(report.get("playwright_failed") or 0) > 0:
        failures.append(f"playwright_failed={report.get('playwright_failed')}")
    if report.get("regression_passed") is False:
        failures.append("backtest_regression")
    return failures


def build_context(state: LoopState, iteration: int) -> LoopContext:
    recent_ideas = state.idea_history[-5:] if len(state.idea_history) >= 5 else state.idea_history
    changed_files = _git_changed_files()

    last_report = _last_test_report(iteration)
    test_pass_rate = 1.0
    total = int(last_report.get("pytest_total") or 0)
    passed = int(last_report.get("pytest_passed") or 0)
    if total > 0:
        test_pass_rate = passed / total
    elif last_report.get("overall_passed") is False:
        test_pass_rate = 0.0

    backtest_metrics: dict[str, object] = {}
    if state.metrics_history:
        backtest_metrics = state.metrics_history[-1]

    cloud_url = read_cloud_run_url()
    cloud_health: dict[str, object] = {}
    if cloud_url:
        try:
            ok, payload = verify_cloud_health(cloud_url)
            cloud_health = {"ok": ok, **payload}
        except httpx.HTTPError:
            cloud_health = {"ok": False, "error": "cloud health fetch failed"}

    return LoopContext(
        iteration=iteration,
        recent_ideas=recent_ideas,
        test_pass_rate=test_pass_rate,
        backtest_metrics=backtest_metrics,
        changed_files=changed_files,
        compact_summary=state.last_compact_summary,
        cloud_run_url=cloud_url,
        cloud_health=cloud_health,
        last_test_failures=_failure_messages(last_report),
    )
