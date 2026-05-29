"""Git commit + push after successful loop iterations."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

LOGGER = logging.getLogger(__name__)


def git_commit_and_push(iteration: int, message: str, *, dry_run: bool = False) -> bool:
    workspace = Path("/home/aarav/Aarav/Autopilot")
    if dry_run:
        LOGGER.info("[Dry Run] Would git commit: %s", message)
        return True

    try:
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=workspace,
            capture_output=True,
            text=True,
            check=True,
        )
        if not status.stdout.strip():
            LOGGER.info("Iteration %s: no git changes to commit", iteration)
            return True

        subprocess.run(["git", "add", "-A"], cwd=workspace, check=True)
        subprocess.run(
            ["git", "commit", "-m", message],
            cwd=workspace,
            check=True,
        )
        push = subprocess.run(
            [
                "git",
                "-c",
                "credential.helper=!gh auth git-credential",
                "push",
                "origin",
                "HEAD",
            ],
            cwd=workspace,
            capture_output=True,
            text=True,
        )
        if push.returncode != 0:
            push = subprocess.run(
                ["git", "push", "origin", "HEAD"],
                cwd=workspace,
                capture_output=True,
                text=True,
            )
        if push.returncode != 0:
            LOGGER.warning("git push failed: %s", push.stderr)
            return False
        LOGGER.info("Iteration %s pushed to origin", iteration)
        return True
    except subprocess.CalledProcessError as exc:
        LOGGER.error("Git operation failed at iteration %s: %s", iteration, exc)
        return False
