from __future__ import annotations

import dataclasses
import json
import logging
import os
import re
import subprocess
import time
from pathlib import Path

import httpx

from loop_modules.gcloud_deployer import read_cloud_run_url, verify_cloud_health
from loop_modules.models import ImplementationPlan, LoopContext, TestResult

LOGGER = logging.getLogger(__name__)

_PYTEST_SUMMARY = re.compile(
    r"(?P<passed>\d+) passed(?:, (?P<skipped>\d+) skipped)?(?:, (?P<failed>\d+) failed)?(?:, (?P<errors>\d+) error)?",
    re.I,
)


class IterationTestRunner:
    def __init__(self, is_dry_run: bool = False):
        self.is_dry_run = is_dry_run
        self.workspace = Path("/home/aarav/Aarav/Autopilot")

    def run_baseline(self, context: LoopContext) -> TestResult:
        """Pre-change gate: pytest + local API smoke (+ cloud if URL configured)."""
        return self._execute(context.iteration, plan=None, context=context, include_playwright=False)

    def run_all(self, plan: ImplementationPlan, context: LoopContext) -> TestResult:
        """Post-change verification including targeted Playwright smoke."""
        return self._execute(context.iteration, plan=plan, context=context, include_playwright=True)

    def _execute(
        self,
        iteration: int,
        *,
        plan: ImplementationPlan | None,
        context: LoopContext,
        include_playwright: bool,
    ) -> TestResult:
        if self.is_dry_run:
            LOGGER.info("[Dry Run] Skipping test suite execution")
            res = TestResult(
                pytest_passed=10,
                pytest_total=10,
                pytest_failed=0,
                tsc_passed=True,
                playwright_passed=2,
                playwright_total=2,
                playwright_failed=0,
                playwright_screenshots=[],
                api_smoke_passed=True,
                cloud_smoke_passed=True,
                cloud_run_url=read_cloud_run_url(),
                backtest_sharpe=2.5,
                backtest_win_rate=0.6,
                regression_passed=True,
                overall_passed=True,
            )
            self._save_report(iteration, res)
            return res

        LOGGER.info("Step A: Python unit tests (pytest exit code + summary line)")
        pytest_passed, pytest_total, pytest_failed = self._run_pytest(plan)

        LOGGER.info("Step B: TypeScript type check")
        tsc_passed = self._run_tsc(plan)

        LOGGER.info("Step C: Local backend API smoke (backend_api.py)")
        api_smoke_passed = self._run_api_smoke()

        playwright_passed, playwright_total, playwright_failed = 0, 0, 0
        if include_playwright:
            LOGGER.info("Step D: Playwright smoke (smoke.spec.ts only)")
            playwright_passed, playwright_total, playwright_failed = self._run_playwright_smoke()
        else:
            playwright_passed, playwright_total, playwright_failed = 0, 0, 0

        LOGGER.info("Step E: Cloud Run smoke")
        cloud_smoke_passed, cloud_url = self._run_cloud_smoke()

        LOGGER.info("Step F: Backtest regression check")
        backtest_sharpe, backtest_win_rate, regression_passed = self._run_backtest(context)

        overall_passed = (
            pytest_failed == 0
            and pytest_passed > 0
            and tsc_passed
            and api_smoke_passed
            and (not include_playwright or playwright_failed == 0)
            and cloud_smoke_passed
            and regression_passed
        )

        res = TestResult(
            pytest_passed=pytest_passed,
            pytest_total=pytest_total,
            pytest_failed=pytest_failed,
            tsc_passed=tsc_passed,
            playwright_passed=playwright_passed,
            playwright_total=playwright_total,
            playwright_failed=playwright_failed,
            playwright_screenshots=[],
            api_smoke_passed=api_smoke_passed,
            cloud_smoke_passed=cloud_smoke_passed,
            cloud_run_url=cloud_url,
            backtest_sharpe=backtest_sharpe,
            backtest_win_rate=backtest_win_rate,
            regression_passed=regression_passed,
            overall_passed=overall_passed,
        )
        self._save_report(iteration, res)
        return res

    def _run_pytest(self, plan: ImplementationPlan | None) -> tuple[int, int, int]:
        cmd = ["python", "-m", "pytest", "tests/", "-q", "--tb=short"]
        if plan and plan.test_commands:
            for tc in plan.test_commands:
                if "pytest" in tc and tc.startswith("python"):
                    cmd = tc.split()
                    break

        try:
            result = subprocess.run(
                cmd,
                cwd=self.workspace,
                capture_output=True,
                text=True,
                timeout=int(os.getenv("LOOP_PYTEST_TIMEOUT_SEC", "600")),
            )
            combined = (result.stdout or "") + "\n" + (result.stderr or "")
            match = None
            for line in reversed(combined.splitlines()):
                m = _PYTEST_SUMMARY.search(line)
                if m:
                    match = m
                    break
            if match:
                passed = int(match.group("passed"))
                failed = int(match.group("failed") or 0) + int(match.group("errors") or 0)
                skipped = int(match.group("skipped") or 0)
                total = passed + failed + skipped
                if result.returncode != 0 and failed == 0:
                    failed = 1
                    total = max(total, passed + failed)
                return passed, total, failed
            if result.returncode == 0:
                return 1, 1, 0
            LOGGER.error("Pytest failed without summary line:\n%s", combined[-3000:])
            return 0, 1, 1
        except Exception as exc:
            LOGGER.error("Pytest failed to run: %s", exc)
            return 0, 1, 1

    def _run_tsc(self, plan: ImplementationPlan | None) -> bool:
        touches_frontend = False
        if plan:
            touches_frontend = any(
                s.file.startswith("autopilot-local/frontend") for s in plan.steps
            )
        if plan and not touches_frontend:
            return True
        try:
            frontend_dir = self.workspace / "autopilot-local" / "frontend"
            result = subprocess.run(
                ["npx", "tsc", "--noEmit"],
                cwd=frontend_dir,
                capture_output=True,
                text=True,
                timeout=180,
            )
            if result.returncode != 0:
                LOGGER.error("tsc failed:\n%s", (result.stderr or result.stdout)[-2000:])
            return result.returncode == 0
        except Exception as exc:
            LOGGER.error("TSC failed to run: %s", exc)
            return False

    def _run_playwright_smoke(self) -> tuple[int, int, int]:
        frontend_dir = self.workspace / "autopilot-local" / "frontend"
        env = os.environ.copy()
        env.setdefault("APEX_HEALTH_URL", "http://127.0.0.1:8000/health")
        env.setdefault("PLAYWRIGHT_HEADED", "0")
        try:
            result = subprocess.run(
                ["npx", "playwright", "test", "tests/e2e/smoke.spec.ts", "--reporter=line"],
                cwd=frontend_dir,
                capture_output=True,
                text=True,
                env=env,
                timeout=int(os.getenv("LOOP_PLAYWRIGHT_TIMEOUT_SEC", "300")),
            )
            combined = (result.stdout or "") + "\n" + (result.stderr or "")
            passed = len(re.findall(r"\bpassed\b", combined, re.I))
            failed = len(re.findall(r"\bfailed\b", combined, re.I))
            if result.returncode == 0:
                total = max(passed, 2)
                return total, total, 0
            LOGGER.error("Playwright smoke failed:\n%s", combined[-4000:])
            return 0, max(1, failed or 1), max(1, failed or 1)
        except Exception as exc:
            LOGGER.error("Playwright failed to run: %s", exc)
            return 0, 1, 1

    def _run_api_smoke(self) -> bool:
        port = int(os.getenv("LOOP_API_SMOKE_PORT", "8010"))
        env = os.environ.copy()
        env["PYTHONPATH"] = f"{self.workspace / 'src'}:{self.workspace / 'autopilot-local' / 'backend'}"
        env.setdefault("SHOWCASE_MODE", "true")
        env.setdefault("AUTH_ENABLED", "true")
        env.setdefault("APEX_ARB_SCAN_LOOP", "false")
        proc = None
        base = f"http://127.0.0.1:{port}"
        try:
            proc = subprocess.Popen(
                [
                    "python",
                    "-m",
                    "uvicorn",
                    "backend_api:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(port),
                ],
                cwd=self.workspace,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            deadline = time.time() + 90
            while time.time() < deadline:
                try:
                    with httpx.Client(timeout=5.0) as client:
                        r = client.get(f"{base}/health")
                        if r.status_code == 200:
                            break
                except Exception:
                    pass
                if proc.poll() is not None:
                    err = proc.stderr.read().decode() if proc.stderr else ""
                    LOGGER.error("backend_api exited early: %s", err[-2000:])
                    return False
                time.sleep(1)
            else:
                LOGGER.error("backend_api smoke: startup timeout on %s", base)
                return False

            with httpx.Client(timeout=15.0) as client:
                health = client.get(f"{base}/health")
                guest = client.post(f"{base}/api/auth/guest")
                arbs = client.get(f"{base}/api/arb/opportunities")
                ok = (
                    health.status_code == 200
                    and guest.status_code in (200, 201)
                    and arbs.status_code == 200
                )
                if not ok:
                    LOGGER.error(
                        "API smoke statuses health=%s guest=%s arbs=%s",
                        health.status_code,
                        guest.status_code,
                        arbs.status_code,
                    )
                return ok
        except Exception as exc:
            LOGGER.error("API smoke test failed: %s", exc)
            return False
        finally:
            if proc and proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    proc.kill()

    def _run_cloud_smoke(self) -> tuple[bool, str]:
        url = read_cloud_run_url()
        if not url:
            LOGGER.warning("No CLOUD_RUN_URL configured — skipping cloud smoke (set data/cloud_run_url.txt)")
            return True, ""
        ok, payload = verify_cloud_health(url)
        if not ok:
            LOGGER.error("Cloud smoke failed for %s: %s", url, payload)
        return ok, url

    def _run_backtest(self, context: LoopContext) -> tuple[float, float, bool]:
        try:
            import sys

            src = str(self.workspace / "src")
            if src not in sys.path:
                sys.path.insert(0, src)

            from apex.core.config import get_settings
            from apex.repositories.sqlite_store import SQLiteStore
            from apex.services.backtest_engine import BacktestEngine

            settings = get_settings()
            store = SQLiteStore(settings.sqlite_path)
            engine = BacktestEngine(settings=settings, store=store)
            result = engine.run(lookback_days=90)

            prev_sharpe = float(context.backtest_metrics.get("sharpe", result.sharpe))
            regression_passed = result.sharpe >= prev_sharpe - 0.05
            return result.sharpe, result.win_rate, regression_passed
        except Exception as exc:
            LOGGER.error("Backtest regression check failed: %s", exc)
            return 0.0, 0.0, False

    def _save_report(self, iteration: int, res: TestResult) -> None:
        path = self.workspace / "data" / "loop_logs" / f"iteration_{iteration:04d}_tests.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(dataclasses.asdict(res), f, indent=2)
