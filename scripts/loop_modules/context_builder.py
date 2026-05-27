from __future__ import annotations

import subprocess
import os
import json
from pathlib import Path

from loop_modules.models import LoopContext, LoopState

def build_context(state: LoopState, iteration: int) -> LoopContext:
    # recent ideas (last 5 outcomes)
    recent_ideas = state.idea_history[-5:] if len(state.idea_history) >= 5 else state.idea_history
    
    # git status --short
    try:
        git_status_out = subprocess.check_output(["git", "status", "--short"], text=True, cwd="/home/aarav/Aarav/Autopilot")
        changed_files = [line.split()[-1] for line in git_status_out.strip().split('\n') if line]
    except Exception:
        changed_files = []

    # get test pass rate from last test report if exists
    test_pass_rate = 1.0
    if iteration > 1:
        last_iter = iteration - 1
        log_path = Path(f"/home/aarav/Aarav/Autopilot/data/loop_logs/iteration_{last_iter:04d}_tests.json")
        if log_path.exists():
            try:
                with open(log_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    total = data.get("pytest_total", 0)
                    passed = data.get("pytest_passed", 0)
                    if total > 0:
                        test_pass_rate = passed / total
            except Exception:
                pass

    # current backtest metrics
    backtest_metrics = {}
    if state.metrics_history:
        backtest_metrics = state.metrics_history[-1]

    return LoopContext(
        iteration=iteration,
        recent_ideas=recent_ideas,
        test_pass_rate=test_pass_rate,
        backtest_metrics=backtest_metrics,
        changed_files=changed_files,
        compact_summary=state.last_compact_summary
    )
