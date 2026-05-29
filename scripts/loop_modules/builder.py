from __future__ import annotations

import logging
import shutil
import time
from pathlib import Path
import py_compile

from loop_modules.models import ImplementationPlan, LoopContext, BuildResult

LOGGER = logging.getLogger(__name__)

class IterationBuilder:
    def __init__(self, is_dry_run: bool = False):
        self.is_dry_run = is_dry_run
        self.workspace = Path("/home/aarav/Aarav/Autopilot")

    def _snapshot_files(self, iteration: int, plan: ImplementationPlan) -> Path:
        snapshot_dir = self.workspace / "data" / "loop_snapshots" / f"iteration_{iteration:04d}"
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        
        for step in plan.steps:
            src = self.workspace / step.file
            if src.exists() and src.is_file():
                # create matching directory structure in snapshot
                dst = snapshot_dir / step.file
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
        return snapshot_dir

    def _rollback(self, snapshot_dir: Path, plan: ImplementationPlan):
        LOGGER.critical(f"Rolling back iteration from {snapshot_dir}")
        for step in plan.steps:
            dst = self.workspace / step.file
            src = snapshot_dir / step.file
            if src.exists():
                shutil.copy2(src, dst)
            elif dst.exists():
                # it was created during this iteration, so delete it
                dst.unlink()

    def build(self, plan: ImplementationPlan, context: LoopContext) -> BuildResult:
        start_time = time.time()
        snapshot_dir = None
        
        if self.is_dry_run:
            LOGGER.info("[Dry Run] Skipping file modifications")
            return BuildResult(success=True, files_changed=[s.file for s in plan.steps], errors=[], duration_seconds=0.1)

        snapshot_dir = self._snapshot_files(context.iteration, plan)
        
        from apex.core.config import get_settings
        settings = get_settings()
        client = settings.get_llm_client()
        if not client:
            if plan.steps:
                msg = "No LLM client but plan has steps — cannot apply changes"
                LOGGER.error(msg)
                return BuildResult(success=False, files_changed=[], errors=[msg], duration_seconds=0.0)
            LOGGER.warning("No LLM client — test-only iteration (empty plan)")
            return BuildResult(success=True, files_changed=[], errors=[], duration_seconds=0.0)

        errors = []
        files_changed = []

        for step in plan.steps:
            target_path = self.workspace / step.file
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            current_content = ""
            if target_path.exists():
                with open(target_path, "r", encoding="utf-8") as f:
                    current_content = f.read()

            prompt = f"""You are the Iteration Builder. Apply this change:
File: {step.file}
Action: {step.action}
Description: {step.description}

Current File Content:
```python
{current_content}
```

Respond with ONLY the exact, complete new file content (or empty if deleting). Do not include markdown fences around the entire response, just raw code. If you must use fences, use them exactly around the code block and nothing else.
"""
            try:
                response = client.chat.completions.create(
                    model=getattr(settings, "llm_model", "llama3.2:3b"),
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=8192,
                    temperature=0.1
                )
                raw = response.choices[0].message.content or ""
                # Strip leading/trailing markdown fences if present
                if raw.startswith("```"):
                    lines = raw.split("\n")
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].startswith("```"):
                        lines = lines[:-1]
                    raw = "\n".join(lines)
                
                if step.action == "DELETE":
                    if target_path.exists():
                        target_path.unlink()
                else:
                    with open(target_path, "w", encoding="utf-8") as f:
                        f.write(raw)
                    files_changed.append(step.file)

                # If Python, compile immediately
                if step.file.endswith(".py") and step.action != "DELETE":
                    try:
                        py_compile.compile(str(target_path), doraise=True)
                    except py_compile.PyCompileError as pce:
                        LOGGER.warning(f"Syntax error in {step.file}: {pce}. Attempting self-correction.")
                        # Self-correction attempt
                        correction_prompt = f"The following code has a syntax error:\n{pce}\n\nCode:\n```python\n{raw}\n```\n\nFix the syntax error and return ONLY the corrected complete code block."
                        corr_resp = client.chat.completions.create(
                            model=getattr(settings, "llm_model", "llama3.2:3b"),
                            messages=[{"role": "user", "content": correction_prompt}],
                            max_tokens=8192,
                            temperature=0.1
                        )
                        c_raw = corr_resp.choices[0].message.content or ""
                        if c_raw.startswith("```"):
                            lines = c_raw.split("\n")
                            if lines[0].startswith("```"):
                                lines = lines[1:]
                            if lines and lines[-1].startswith("```"):
                                lines = lines[:-1]
                            c_raw = "\n".join(lines)
                        
                        with open(target_path, "w", encoding="utf-8") as f:
                            f.write(c_raw)
                        # Compile again, if fails, it adds to errors
                        py_compile.compile(str(target_path), doraise=True)

            except Exception as e:
                LOGGER.error(f"Failed to build step {step.file}: {e}")
                errors.append(f"Step {step.file} failed: {e}")

        success = len(errors) <= 2
        if not success and snapshot_dir:
            self._rollback(snapshot_dir, plan)

        duration = time.time() - start_time
        
        # Save build log
        log_path = self.workspace / "data" / "loop_logs" / f"iteration_{context.iteration:04d}_build.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(f"Success: {success}\nDuration: {duration:.2f}s\nErrors:\n" + "\n".join(errors))

        return BuildResult(
            success=success,
            files_changed=files_changed,
            errors=errors,
            duration_seconds=duration
        )
