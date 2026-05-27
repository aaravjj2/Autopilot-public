from __future__ import annotations

import json
import logging
import subprocess
import time
from pathlib import Path

import httpx

from loop_modules.models import ImplementationPlan, LoopContext, TestResult

LOGGER = logging.getLogger(__name__)

class IterationTestRunner:
    def __init__(self, is_dry_run: bool = False):
        self.is_dry_run = is_dry_run
        self.workspace = Path("/home/aarav/Aarav/Autopilot")

    def run_all(self, plan: ImplementationPlan, context: LoopContext) -> TestResult:
        if self.is_dry_run:
            LOGGER.info("[Dry Run] Skipping test suite execution")
            res = TestResult(
                pytest_passed=10, pytest_total=10, pytest_failed=0,
                tsc_passed=True,
                playwright_passed=5, playwright_total=5, playwright_failed=0, playwright_screenshots=[],
                api_smoke_passed=True,
                backtest_sharpe=2.5, backtest_win_rate=0.6, regression_passed=True,
                overall_passed=True
            )
            self._save_report(context.iteration, res)
            return res

        LOGGER.info("Step A: Python unit tests")
        pytest_passed, pytest_total, pytest_failed = self._run_pytest()

        LOGGER.info("Step B: TypeScript type check")
        tsc_passed = self._run_tsc()

        LOGGER.info("Step C: Playwright E2E tests")
        playwright_passed, playwright_total, playwright_failed = self._run_playwright()

        LOGGER.info("Step D: Backend API smoke test")
        api_smoke_passed = self._run_api_smoke()

        LOGGER.info("Step E: Backtest regression check")
        backtest_sharpe, backtest_win_rate, regression_passed = self._run_backtest(context)

        overall_passed = (
            pytest_failed == 0 and
            tsc_passed and
            playwright_failed == 0 and
            api_smoke_passed and
            regression_passed
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
            backtest_sharpe=backtest_sharpe,
            backtest_win_rate=backtest_win_rate,
            regression_passed=regression_passed,
            overall_passed=overall_passed
        )

        self._save_report(context.iteration, res)
        return res

    def _run_pytest(self) -> tuple[int, int, int]:
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "tests/", "-q", "--tb=short"],
                cwd=self.workspace,
                capture_output=True,
                text=True
            )
            # basic parsing
            passed = result.stdout.count("PASSED") + result.stdout.count(".")
            failed = result.stdout.count("FAILED") + result.stdout.count("F")
            return passed, passed + failed, failed
        except Exception as e:
            LOGGER.error(f"Pytest failed to run: {e}")
            return 0, 0, 1

    def _run_tsc(self) -> bool:
        try:
            frontend_dir = self.workspace / "autopilot-local" / "frontend"
            result = subprocess.run(
                ["npx", "tsc", "--noEmit"],
                cwd=frontend_dir,
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception as e:
            LOGGER.error(f"TSC failed to run: {e}")
            return False

    def _run_playwright(self) -> tuple[int, int, int]:
        try:
            frontend_dir = self.workspace / "autopilot-local" / "frontend"
            result = subprocess.run(
                ["npx", "playwright", "test", "--reporter=json"],
                cwd=frontend_dir,
                capture_output=True,
                text=True
            )
            # try parsing json
            try:
                data = json.loads(result.stdout)
                total = data.get("stats", {}).get("expected", 0) + data.get("stats", {}).get("unexpected", 0)
                failed = data.get("stats", {}).get("unexpected", 0)
                passed = data.get("stats", {}).get("expected", 0)
                return passed, total, failed
            except Exception:
                # fallback
                if result.returncode == 0:
                    return 1, 1, 0
                return 0, 1, 1
        except Exception as e:
            LOGGER.error(f"Playwright failed to run: {e}")
            return 0, 0, 1

    def _run_api_smoke(self) -> bool:
        backend_dir = self.workspace / "autopilot-local" / "backend"
        proc = None
        try:
            proc = subprocess.Popen(
                ["uvicorn", "main:app", "--port", "8001"],
                cwd=backend_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            time.sleep(5)  # wait for startup
            
            with httpx.Client(timeout=10.0) as client:
                r1 = client.get("http://localhost:8001/api/opportunities")
                r2 = client.get("http://localhost:8001/api/arb/backtest")
                
            return r1.status_code == 200 and r2.status_code == 200
        except Exception as e:
            LOGGER.error(f"API smoke test failed: {e}")
            return False
        finally:
            if proc:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()

    def _run_backtest(self, context: LoopContext) -> tuple[float, float, bool]:
        try:
            import sys
            if str(self.workspace / "src") not in sys.path:
                sys.path.append(str(self.workspace / "src"))
                
            from apex.core.config import get_settings
            from apex.repositories.sqlite_store import SQLiteStore
            from apex.services.backtest_engine import BacktestEngine
            
            settings = get_settings()
            store = SQLiteStore(settings.sqlite_path)
            engine = BacktestEngine(settings=settings, store=store)
            result = engine.run(lookback_days=90)
            
            prev_sharpe = context.backtest_metrics.get("sharpe", result.sharpe)
            regression_passed = result.sharpe >= prev_sharpe - 0.05 and result.win_rate >= 0.0
            
            return result.sharpe, result.win_rate, regression_passed
        except Exception as e:
            LOGGER.error(f"Backtest regression check failed: {e}")
            return 0.0, 0.0, False

    def _save_report(self, iteration: int, res: TestResult):
        import dataclasses
        path = self.workspace / "data" / "loop_logs" / f"iteration_{iteration:04d}_tests.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(dataclasses.asdict(res), f, indent=2)
