from __future__ import annotations

import json
import logging
from pathlib import Path

from loop_modules.models import Idea, LoopContext, ImplementationPlan, PlanStep
from loop_modules.plan_templates import plan_for_idea

LOGGER = logging.getLogger(__name__)


class IterationPlanner:
    def __init__(self, is_dry_run: bool = False):
        self.is_dry_run = is_dry_run

    def plan(self, idea: Idea, context: LoopContext) -> ImplementationPlan:
        if self.is_dry_run:
            LOGGER.info("[Dry Run] Generating mock plan for %s", idea.title)
            plan = ImplementationPlan(
                steps=[PlanStep(file="src/apex/main.py", action="MODIFY", description="Mock step")],
                test_commands=["python -m pytest tests/ -q --tb=short"],
                rollback_steps=["git restore ."],
                expected_artifacts=["/dashboard/arb-radar"],
            )
            self._save_plan(context.iteration, plan)
            return plan

        rule_plan = plan_for_idea(idea)
        if rule_plan and rule_plan.steps:
            LOGGER.info("Using rule-based plan for: %s (%d steps)", idea.title, len(rule_plan.steps))
            self._save_plan(context.iteration, rule_plan)
            return rule_plan

        from apex.core.config import get_settings

        settings = get_settings()
        client = settings.get_llm_client()
        if not client:
            LOGGER.warning("No LLM client — using metadata-derived plan for %s", idea.title)
            fallback = plan_for_idea(idea) or ImplementationPlan(
                steps=[],
                test_commands=["python -m pytest tests/ -q --tb=short"],
                rollback_steps=["git restore ."],
                expected_artifacts=[],
            )
            self._save_plan(context.iteration, fallback)
            return fallback

        cloud_hint = json.dumps(context.cloud_health)[:800]
        failures_hint = "; ".join(context.last_test_failures[:5])

        prompt = f"""You are the Iteration Planner.
Break down this Idea into an ImplementationPlan with concrete, file-specific steps.

Idea Title: {idea.title}
Idea Description: {idea.description}
Files Likely Affected: {idea.files_likely_affected}
Test Strategy: {idea.test_strategy}
Cloud Health: {cloud_hint}
Recent Test Failures: {failures_hint or "none"}

Return ONLY valid JSON:
{{
  "steps": [
    {{
      "file": "path/to/file.py",
      "action": "CREATE" | "MODIFY" | "DELETE",
      "description": "Exactly what to change in this file"
    }}
  ],
  "test_commands": ["python -m pytest tests/... -q --tb=short"],
  "rollback_steps": ["git restore path/to/file.py"],
  "expected_artifacts": ["/health"]
}}
"""
        try:
            response = client.chat.completions.create(
                model=getattr(settings, "llm_model", "llama3.2:3b"),
                messages=[
                    {
                        "role": "system",
                        "content": "You are a quantitative software engineer generating strictly typed JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=1500,
                temperature=0.3,
            )
            raw = response.choices[0].message.content or "{}"
            if "```" in raw:
                for block in raw.split("```"):
                    if block.strip().startswith("{"):
                        raw = block
                        if raw.startswith("json"):
                            raw = raw[4:]
                        break

            parsed = json.loads(raw.strip())
            steps = [
                PlanStep(
                    file=s.get("file", ""),
                    action=s.get("action", "MODIFY"),
                    description=s.get("description", ""),
                )
                for s in parsed.get("steps", [])
            ]
            plan = ImplementationPlan(
                steps=steps,
                test_commands=parsed.get("test_commands", ["python -m pytest tests/ -q --tb=short"]),
                rollback_steps=parsed.get("rollback_steps", []),
                expected_artifacts=parsed.get("expected_artifacts", []),
            )
            if not plan.steps and rule_plan:
                plan = rule_plan
            self._save_plan(context.iteration, plan)
            return plan

        except Exception as exc:
            LOGGER.error("IterationPlanner LLM failed: %s", exc)
            fallback = plan_for_idea(idea) or ImplementationPlan(
                steps=[],
                test_commands=["python -m pytest tests/ -q --tb=short"],
                rollback_steps=[],
                expected_artifacts=[],
            )
            self._save_plan(context.iteration, fallback)
            LOGGER.warning("Using fallback plan (%d steps)", len(fallback.steps))
            return fallback

    def _save_plan(self, iteration: int, plan: ImplementationPlan) -> None:
        import dataclasses

        path = Path(f"/home/aarav/Aarav/Autopilot/data/loop_plans/iteration_{iteration:04d}_plan.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(dataclasses.asdict(plan), f, indent=2)
