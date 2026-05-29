from __future__ import annotations

import json
import logging
from pathlib import Path

from loop_modules.models import Idea, LoopContext, ImplementationPlan, PlanStep

LOGGER = logging.getLogger(__name__)

class IterationPlanner:
    def __init__(self, is_dry_run: bool = False):
        self.is_dry_run = is_dry_run

    def plan(self, idea: Idea, context: LoopContext) -> ImplementationPlan:
        if self.is_dry_run:
            LOGGER.info(f"[Dry Run] Generating mock plan for {idea.title}")
            plan = ImplementationPlan(
                steps=[PlanStep(file="src/apex/main.py", action="MODIFY", description="Mock step")],
                test_commands=["pytest tests/"],
                rollback_steps=["git restore ."],
                expected_artifacts=["/dashboard/arb-radar"]
            )
            self._save_plan(context.iteration, plan)
            return plan

        from apex.core.config import get_settings
        settings = get_settings()
        client = settings.get_llm_client()
        if not client:
            raise RuntimeError("No LLM client configured for IterationPlanner")

        prompt = f"""You are the Iteration Planner.
Your job is to break down the following Idea into an ImplementationPlan.

Idea Title: {idea.title}
Idea Description: {idea.description}
Files Likely Affected: {idea.files_likely_affected}
Test Strategy: {idea.test_strategy}

Return ONLY valid JSON matching this schema:
{{
  "steps": [
    {{
      "file": "path/to/file.py",
      "action": "CREATE" | "MODIFY" | "DELETE",
      "description": "Exactly what to change in this file"
    }}
  ],
  "test_commands": [
    "exact shell commands to verify success"
  ],
  "rollback_steps": [
    "how to undo if tests fail"
  ],
  "expected_artifacts": [
    "paths like /dashboard/arb-radar"
  ]
}}
"""
        try:
            response = client.chat.completions.create(
                model=getattr(settings, "llm_model", "llama3.2:3b"),
                messages=[
                    {"role": "system", "content": "You are a quantitative software engineer generating strictly typed JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500,
                temperature=0.3
            )
            raw = response.choices[0].message.content or "{}"
            if "```" in raw:
                lines = raw.split("```")
                for block in lines:
                    if block.strip().startswith("{"):
                        raw = block
                        if raw.startswith("json"):
                            raw = raw[4:]
                        break

            parsed = json.loads(raw.strip())
            
            steps = []
            for s in parsed.get("steps", []):
                steps.append(PlanStep(
                    file=s.get("file", ""),
                    action=s.get("action", "MODIFY"),
                    description=s.get("description", "")
                ))
                
            plan = ImplementationPlan(
                steps=steps,
                test_commands=parsed.get("test_commands", []),
                rollback_steps=parsed.get("rollback_steps", []),
                expected_artifacts=parsed.get("expected_artifacts", [])
            )
            
            self._save_plan(context.iteration, plan)
            return plan

        except Exception as e:
            LOGGER.error(f"IterationPlanner failed: {e}")
            plan = ImplementationPlan(
                steps=[],
                test_commands=["python -m pytest tests/ -q --tb=no"],
                rollback_steps=[],
                expected_artifacts=[],
            )
            self._save_plan(context.iteration, plan)
            LOGGER.warning("Using test-only fallback plan (LLM unavailable)")
            return plan

    def _save_plan(self, iteration: int, plan: ImplementationPlan):
        import dataclasses
        path = Path(f"/home/aarav/Aarav/Autopilot/data/loop_plans/iteration_{iteration:04d}_plan.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(dataclasses.asdict(plan), f, indent=2)
