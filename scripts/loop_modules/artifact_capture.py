from __future__ import annotations

import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path

from loop_modules.models import Artifact, ImplementationPlan

LOGGER = logging.getLogger(__name__)

class ArtifactCapture:
    def __init__(self, is_dry_run: bool = False):
        self.is_dry_run = is_dry_run
        self.workspace = Path("/home/aarav/Aarav/Autopilot")

    def capture_all(self, iteration: int, plan: ImplementationPlan) -> list[Artifact]:
        artifacts = []
        base_dir = self.workspace / "data" / "artifacts" / f"iteration_{iteration:04d}"
        base_dir.mkdir(parents=True, exist_ok=True)
        
        ts = datetime.utcnow().isoformat()

        # 1. Diff snapshots
        diff_dir = base_dir / "diffs"
        diff_dir.mkdir(exist_ok=True)
        for step in plan.steps:
            if step.file.endswith(".py") or step.file.endswith(".ts") or step.file.endswith(".tsx"):
                try:
                    diff_out = subprocess.check_output(
                        ["git", "diff", "--", step.file],
                        cwd=self.workspace,
                        text=True
                    )
                    if diff_out:
                        diff_path = diff_dir / f"{Path(step.file).name}.diff"
                        with open(diff_path, "w", encoding="utf-8") as f:
                            f.write(diff_out)
                        artifacts.append(Artifact(type="diff", path=str(diff_path), iteration=iteration, timestamp=ts))
                except Exception as e:
                    LOGGER.warning(f"Failed to capture diff for {step.file}: {e}")

        # 2. Screenshots (if not dry run)
        if not self.is_dry_run:
            from playwright.sync_api import sync_playwright
            screenshot_dir = base_dir / "screenshots"
            screenshot_dir.mkdir(exist_ok=True)
            
            pages_to_capture = set(["/dashboard/arb-radar", "/dashboard/analytics"] + plan.expected_artifacts)
            
            # Start a temporary frontend server if needed, or assume it's running. 
            # The prompt implies we just use Playwright to open the pages. Let's assume port 3000 is up, or we just try.
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    context = browser.new_context(record_video_dir=str(base_dir / "videos/"))
                    page = context.new_page()
                    
                    for p_url in pages_to_capture:
                        if p_url.startswith("/"):
                            url = f"http://localhost:3000{p_url}"
                        else:
                            url = p_url
                        try:
                            page.goto(url, timeout=5000)
                            safe_name = p_url.replace("/", "_").strip("_") or "home"
                            path = screenshot_dir / f"{safe_name}.png"
                            page.screenshot(path=str(path), full_page=True)
                            artifacts.append(Artifact(type="screenshot", path=str(path), iteration=iteration, timestamp=ts))
                        except Exception as e:
                            LOGGER.warning(f"Failed to screenshot {url}: {e}")
                    
                    context.close()
                    browser.close()
            except Exception as e:
                LOGGER.warning(f"Playwright screenshot capture failed: {e}")

        # 3. Metrics snapshot
        metrics_path = base_dir / "metrics.json"
        try:
            import sys
            if str(self.workspace / "src") not in sys.path:
                sys.path.append(str(self.workspace / "src"))
            from apex.core.config import get_settings
            from apex.repositories.sqlite_store import SQLiteStore
            from apex.services.backtest_engine import BacktestEngine
            import dataclasses
            
            settings = get_settings()
            store = SQLiteStore(settings.sqlite_path)
            engine = BacktestEngine(settings=settings, store=store)
            result = engine.run(lookback_days=90)
            with open(metrics_path, "w", encoding="utf-8") as f:
                json.dump(dataclasses.asdict(result), f, indent=2)
            artifacts.append(Artifact(type="metrics", path=str(metrics_path), iteration=iteration, timestamp=ts))
        except Exception as e:
            LOGGER.warning(f"Metrics snapshot failed: {e}")

        # Save manifest
        manifest_path = base_dir / "manifest.json"
        import dataclasses
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump([dataclasses.asdict(a) for a in artifacts], f, indent=2)

        return artifacts
