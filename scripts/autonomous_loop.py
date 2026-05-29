from __future__ import annotations

import argparse
import dataclasses
import json
import logging
import os
import time
from pathlib import Path
import sys

workspace = Path(__file__).resolve().parent.parent
if str(workspace) not in sys.path:
    sys.path.append(str(workspace))
if str(workspace / "scripts") not in sys.path:
    sys.path.append(str(workspace / "scripts"))

from loop_modules.models import LoopState  # noqa: E402
from loop_modules.context_builder import build_context  # noqa: E402
from loop_modules.brainstorm import BrainstormEngine  # noqa: E402
from loop_modules.scorer import IdeaScorer  # noqa: E402
from loop_modules.planner import IterationPlanner  # noqa: E402
from loop_modules.builder import IterationBuilder  # noqa: E402
from loop_modules.test_runner import IterationTestRunner  # noqa: E402
from loop_modules.artifact_capture import ArtifactCapture  # noqa: E402
from loop_modules.doc_writer import IterationDocWriter  # noqa: E402
from loop_modules.compactor import LoopCompactor  # noqa: E402
from loop_modules.git_publisher import git_commit_and_push  # noqa: E402
from loop_modules.gcloud_deployer import (  # noqa: E402
    backend_files_changed,
    deploy_to_cloud_run,
    gcloud_available,
    read_cloud_run_url,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
LOGGER = logging.getLogger(__name__)


class BuildFailedError(Exception):
    pass


class BaselineFailedError(Exception):
    pass


class TestsFailedError(Exception):
    pass


def load_or_init_state() -> LoopState:
    path = workspace / "data" / "loop_state.json"
    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
                return LoopState(
                    current_iteration=data.get("current_iteration", 1),
                    completed_iterations=data.get("completed_iterations", []),
                    idea_history=data.get("idea_history", []),
                    failed_iterations=data.get("failed_iterations", []),
                    metrics_history=data.get("metrics_history", []),
                    last_compact_summary=data.get("last_compact_summary", ""),
                )
        except Exception as exc:
            LOGGER.warning("Failed to load state, initializing new: %s", exc)

    return LoopState()


def save_state(state: LoopState) -> None:
    path = workspace / "data" / "loop_state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(dataclasses.asdict(state), f, indent=2)


def _should_deploy(
    iteration: int,
    changed_files: list[str],
    *,
    deploy_every: int,
    force_deploy: bool,
) -> bool:
    if force_deploy:
        return True
    if deploy_every > 0 and iteration % deploy_every == 0:
        return True
    return backend_files_changed(changed_files)


def run_loop(
    start_iteration: int | None = None,
    max_iterations: int = 500,
    is_dry_run: bool = False,
    *,
    skip_baseline: bool = False,
    deploy_every: int = 0,
    force_deploy: bool = False,
) -> None:
    state = load_or_init_state()
    start = start_iteration or state.current_iteration
    sleep_sec = float(os.getenv("LOOP_ITERATION_SLEEP_SEC", "45"))
    runner = IterationTestRunner(is_dry_run)

    if gcloud_available():
        LOGGER.info("gcloud OK — Cloud Run URL: %s", read_cloud_run_url() or "(will capture on deploy)")
    else:
        LOGGER.warning("gcloud not configured — deploy phase will fail until authenticated")

    for i in range(start, start + max_iterations):
        LOGGER.info("=== ITERATION %s (target %s) ===", i, start + max_iterations - 1)
        context = build_context(state, i)
        idea = None
        deploy_result = None

        try:
            if not skip_baseline:
                LOGGER.info("Phase 0: Baseline tests (pre-change gate)")
                baseline = runner.run_baseline(context)
                if not baseline.overall_passed:
                    raise BaselineFailedError(
                        f"baseline failed: pytest={baseline.pytest_failed} "
                        f"api={baseline.api_smoke_passed} cloud={baseline.cloud_smoke_passed}"
                    )

            ideas = BrainstormEngine(is_dry_run).generate_ideas(context)
            idea = IdeaScorer(is_dry_run).score_ideas(ideas, context)
            LOGGER.info("Selected idea: %s", idea.title)

            plan = IterationPlanner(is_dry_run).plan(idea, context)

            build_result = IterationBuilder(is_dry_run).build(plan, context)
            if not build_result.success:
                raise BuildFailedError(build_result.errors)

            test_result = runner.run_all(plan, context)
            if not test_result.overall_passed:
                raise TestsFailedError(
                    f"post-build tests failed: pytest={test_result.pytest_failed} "
                    f"playwright={test_result.playwright_failed}"
                )

            post_build_changed = subprocess_changed_files()
            if _should_deploy(i, post_build_changed, deploy_every=deploy_every, force_deploy=force_deploy):
                LOGGER.info("Phase: Cloud Run deploy (gcloud)")
                deploy_result = deploy_to_cloud_run(i, dry_run=is_dry_run)
                if not deploy_result.success:
                    raise TestsFailedError(f"deploy failed: {deploy_result.error}")
            else:
                LOGGER.info("Skipping deploy (no backend changes this iteration)")

            artifacts = ArtifactCapture(is_dry_run).capture_all(i, plan)
            IterationDocWriter(is_dry_run).document(i, idea, build_result, test_result, artifacts)

            if i % 10 == 0:
                summary = LoopCompactor(is_dry_run).compact(state)
                state.last_compact_summary = summary
                LOGGER.info("Compact summary: %s...", summary[:200])

            pushed = git_commit_and_push(i, f"loop(iter {i}): {idea.title}", dry_run=is_dry_run)
            if not pushed:
                raise TestsFailedError("git push failed")

            state.completed_iterations.append(i)
            state.current_iteration = i + 1
            state.idea_history.append(
                {
                    "iteration": i,
                    "idea": idea.title,
                    "outcome": "SUCCESS",
                    "files_changed": build_result.files_changed,
                    "sharpe": test_result.backtest_sharpe,
                    "deploy_url": deploy_result.service_url if deploy_result else context.cloud_run_url,
                }
            )
            if test_result.backtest_sharpe > 0:
                state.metrics_history.append(
                    {
                        "iteration": i,
                        "sharpe": test_result.backtest_sharpe,
                        "win_rate": test_result.backtest_win_rate,
                        "test_pass_rate": test_result.pytest_passed / max(1, test_result.pytest_total),
                    }
                )
            save_state(state)
            LOGGER.info("Iteration %s SUCCESS", i)

        except Exception as exc:
            LOGGER.error("Iteration %s failed: %s", i, exc)
            state.failed_iterations.append(
                {
                    "iteration": i,
                    "idea": idea.title if idea else "unknown",
                    "error": str(exc),
                }
            )
            state.current_iteration = i + 1
            save_state(state)

        if sleep_sec > 0:
            time.sleep(sleep_sec)


def subprocess_changed_files() -> list[str]:
    import subprocess

    try:
        out = subprocess.check_output(["git", "status", "--short"], text=True, cwd=workspace)
        return [line.split()[-1] for line in out.strip().split("\n") if line.strip()]
    except Exception:
        return []


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Autonomous Improvement Loop")
    parser.add_argument("--start", type=int, help="Starting iteration", default=None)
    parser.add_argument("--max-iterations", type=int, default=1000, help="Max iterations to run")
    parser.add_argument("--dry-run", action="store_true", help="Run without calling LLM or modifying files")
    parser.add_argument("--skip-baseline", action="store_true", help="Skip pre-change baseline tests")
    parser.add_argument(
        "--deploy-every",
        type=int,
        default=int(os.getenv("LOOP_DEPLOY_EVERY", "0")),
        help="Deploy to Cloud Run every N iterations (0 = only when backend files change)",
    )
    parser.add_argument("--force-deploy", action="store_true", help="Always deploy after passing tests")
    args = parser.parse_args()

    run_loop(
        start_iteration=args.start,
        max_iterations=args.max_iterations,
        is_dry_run=args.dry_run,
        skip_baseline=args.skip_baseline,
        deploy_every=args.deploy_every,
        force_deploy=args.force_deploy,
    )
