from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
import sys

# Ensure imports from scripts/ and src/ work correctly
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

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
LOGGER = logging.getLogger(__name__)

class BuildFailedError(Exception):
    pass

def load_or_init_state() -> LoopState:
    path = workspace / "data" / "loop_state.json"
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return LoopState(
                    current_iteration=data.get("current_iteration", 1),
                    completed_iterations=data.get("completed_iterations", []),
                    idea_history=data.get("idea_history", []),
                    failed_iterations=data.get("failed_iterations", []),
                    metrics_history=data.get("metrics_history", []),
                    last_compact_summary=data.get("last_compact_summary", "")
                )
        except Exception as e:
            LOGGER.warning(f"Failed to load state, initializing new: {e}")
            
    return LoopState()

def save_state(state: LoopState):
    path = workspace / "data" / "loop_state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    import dataclasses
    with open(path, "w", encoding="utf-8") as f:
        json.dump(dataclasses.asdict(state), f, indent=2)

def run_loop(start_iteration: int | None = None, max_iterations: int = 500, is_dry_run: bool = False):
    state = load_or_init_state()
    start = start_iteration or state.current_iteration

    for i in range(start, start + max_iterations):
        LOGGER.info(f"=== ITERATION {i}/500 ===")
        context = build_context(state, i)
        idea = None

        try:
            # Phase 1: Brainstorm + Score
            ideas = BrainstormEngine(is_dry_run).generate_ideas(context)
            idea = IdeaScorer(is_dry_run).score_ideas(ideas, context)
            LOGGER.info(f"Selected idea: {idea.title}")

            # Phase 2: Plan
            plan = IterationPlanner(is_dry_run).plan(idea, context)

            # Phase 3: Build
            build_result = IterationBuilder(is_dry_run).build(plan, context)
            if not build_result.success:
                raise BuildFailedError(build_result.errors)

            # Phase 4: Test
            test_result = IterationTestRunner(is_dry_run).run_all(plan, context)

            # Phase 5: Artifacts
            artifacts = ArtifactCapture(is_dry_run).capture_all(i, plan)

            # Phase 6: Document
            IterationDocWriter(is_dry_run).document(i, idea, build_result, test_result, artifacts)

            # Phase 7: Compact every 10 iterations
            if i % 10 == 0:
                summary = LoopCompactor(is_dry_run).compact(state)
                state.last_compact_summary = summary
                LOGGER.info(f"Compact summary: {summary[:200]}...")

            commit_msg = f"loop(iter {i}): {idea.title}"
            git_commit_and_push(i, commit_msg, dry_run=is_dry_run)

            # Save state
            state.completed_iterations.append(i)
            state.current_iteration = i + 1
            state.idea_history.append({
                "iteration": i,
                "idea": idea.title,
                "outcome": "SUCCESS" if test_result.overall_passed else "PARTIAL",
                "files_changed": build_result.files_changed,
                "sharpe": test_result.backtest_sharpe,
            })
            if test_result.backtest_sharpe > 0:
                state.metrics_history.append({
                    "iteration": i,
                    "sharpe": test_result.backtest_sharpe,
                    "win_rate": test_result.backtest_win_rate,
                    "test_pass_rate": (test_result.pytest_passed + test_result.playwright_passed) / max(1, test_result.pytest_total + test_result.playwright_total)
                })
            save_state(state)
            LOGGER.info(f"Iteration {i} complete. Tests: {'PASS' if test_result.overall_passed else 'FAIL'}")

        except Exception as exc:
            LOGGER.error(f"Iteration {i} failed: {exc}")
            state.failed_iterations.append({"iteration": i, "idea": idea.title if idea else "unknown", "error": str(exc)})
            state.current_iteration = i + 1
            save_state(state)
            continue

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Autonomous Improvement Loop")
    parser.add_argument("--start", type=int, help="Starting iteration", default=None)
    parser.add_argument("--max-iterations", type=int, default=1000, help="Max iterations to run")
    parser.add_argument("--dry-run", action="store_true", help="Run without calling LLM or modifying files")
    args = parser.parse_args()
    
    run_loop(start_iteration=args.start, max_iterations=args.max_iterations, is_dry_run=args.dry_run)
