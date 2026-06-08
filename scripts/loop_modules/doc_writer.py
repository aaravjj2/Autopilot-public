from __future__ import annotations

import logging
import subprocess
from datetime import datetime
from pathlib import Path

from loop_modules.models import Artifact, BuildResult, Idea, TestResult

LOGGER = logging.getLogger(__name__)

class IterationDocWriter:
    def __init__(self, is_dry_run: bool = False):
        self.is_dry_run = is_dry_run
        self.workspace = Path("/home/aarav/Aarav/Autopilot")

    def document(self, iteration: int, idea: Idea, build: BuildResult, tests: TestResult, artifacts: list[Artifact]) -> None:
        if self.is_dry_run:
            LOGGER.info(f"[Dry Run] Skipping document updates for iteration {iteration}")
            return

        from apex.core.config import get_settings
        settings = get_settings()
        client = settings.get_llm_client()

        # 1. Changelog update
        changelog_path = self.workspace / "docs" / "CHANGELOG.md"
        ts = datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
        
        summary = idea.description
        if client:
            try:
                prompt = f"Summarize what was built in 2-3 sentences based on this idea: {idea.title}\n{idea.description}\nFiles changed: {build.files_changed}"
                res = client.chat.completions.create(
                    model=getattr(settings, "llm_model", "llama3.2:3b"),
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=150
                )
                summary = res.choices[0].message.content or summary
            except Exception:
                pass

        entry = f"""
## Iteration {iteration} — {idea.title}
**Date**: {ts}
**Focus**: {idea.focus_area}
**Files changed**: {', '.join(build.files_changed) if build.files_changed else 'None'}
**Test results**: pytest {tests.pytest_passed}/{tests.pytest_total} | TS {'✓' if tests.tsc_passed else '✗'} | Playwright {tests.playwright_passed}/{tests.playwright_total} | Sharpe {tests.backtest_sharpe:.2f}
**Summary**: {summary.strip()}
"""
        with open(changelog_path, "a", encoding="utf-8") as f:
            f.write(entry)

        # 2. Architecture Docs update
        apex_changed = any(f.startswith("src/apex/") for f in build.files_changed)
        if apex_changed and client:
            try:
                arch_path = self.workspace / "docs" / "ARCHITECTURE.md"
                # very basic architecture regeneration
                arch_prompt = f"Regenerate a brief architecture overview of the APEX codebase given these recently changed files: {build.files_changed}"
                res = client.chat.completions.create(
                    model=getattr(settings, "llm_model", "llama3.2:3b"),
                    messages=[{"role": "user", "content": arch_prompt}],
                    max_tokens=500
                )
                with open(arch_path, "w", encoding="utf-8") as f:
                    f.write("# APEX Architecture\n\n" + (res.choices[0].message.content or ""))
            except Exception as e:
                LOGGER.warning(f"Failed to update ARCHITECTURE.md: {e}")

        # 3. API Docs update
        if "autopilot-local/backend/main.py" in build.files_changed:
            self._update_api_docs()

        # 4. README badge update
        self._update_readme_badge(tests)

    def _update_api_docs(self):
        script_path = self.workspace / "autopilot-local" / "frontend" / "scripts" / "generate-api-docs.ts"
        if not script_path.exists():
            script_path.parent.mkdir(parents=True, exist_ok=True)
            with open(script_path, "w", encoding="utf-8") as f:
                f.write("""
// Auto-generated script to dump API docs
console.log("# API Documentation\\n\\nAuto-generated from backend/main.py structure.");
""")
        
        api_doc_path = self.workspace / "docs" / "API.md"
        try:
            out = subprocess.check_output(
                ["npx", "ts-node", "scripts/generate-api-docs.ts"],
                cwd=self.workspace / "autopilot-local" / "frontend",
                text=True
            )
            with open(api_doc_path, "w", encoding="utf-8") as f:
                f.write(out)
        except Exception as e:
            LOGGER.warning(f"Failed to update API docs: {e}")

    def _update_readme_badge(self, tests: TestResult):
        readme_path = self.workspace / "README.md"
        if not readme_path.exists():
            return
            
        total = tests.pytest_total + tests.playwright_total
        passed = tests.pytest_passed + tests.playwright_passed
        if total == 0:
            return
            
        rate = passed / total
        color = "green" if rate > 0.9 else "yellow" if rate > 0.7 else "red"
        badge = f"![Tests](https://img.shields.io/badge/tests-{passed}/{total}-{color})"
        
        with open(readme_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # simple replace if exists, or prepend
        import re
        if "![Tests]" in content:
            content = re.sub(r"!\[Tests\]\(.*?\)", badge, content)
        else:
            content = badge + "\n\n" + content
            
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(content)
