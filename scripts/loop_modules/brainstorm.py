from __future__ import annotations

import json
import logging
import os
import time

from loop_modules.models import Idea, LoopContext

LOGGER = logging.getLogger(__name__)

# Circuit breaker: skip LLM calls entirely when the primary provider
# is known-broken (e.g. "organization_restricted"). The var is set by
# the exception handler below and cleared when LLM_CONFIG_REV changes.
_LLM_BROKEN_MARKER = "APEX_LLM_PERMANENTLY_DISABLED"
_LLM_DISABLED_TTL: int = 3600  # 1 hour before retrying


def _llm_is_broken() -> bool:
    """Check if the LLM circuit breaker is active."""
    expiry = os.environ.get(_LLM_BROKEN_MARKER, "")
    if not expiry:
        return False
    try:
        return time.time() < float(expiry)
    except (ValueError, TypeError):
        return False


def _mark_llm_broken() -> None:
    """Permanently disable LLM calls when the provider returns auth/permission errors."""
    os.environ[_LLM_BROKEN_MARKER] = str(time.time() + _LLM_DISABLED_TTL)
    LOGGER.warning(
        "LLM circuit breaker engaged — skipping LLM calls for %d seconds. "
        "Set LLM_CONFIG_REV or restart to retry.",
        _LLM_DISABLED_TTL,
    )

class BrainstormEngine:
    def __init__(self, is_dry_run: bool = False):
        self.is_dry_run = is_dry_run

    def get_focus_area(self, iteration: int) -> str:
        # 1-indexed for the math below
        cycle = ((iteration - 1) % 100) // 10
        areas = [
            "Arb Detection Quality",
            "Risk & Execution",
            "Thesis Quality",
            "Backtesting & Analytics",
            "Observability & Ops",
            "Data & Memory",
            "Frontend & UX",
            "Performance & Scale",
            "Security & Reliability",
            "Developer Experience"
        ]
        return areas[cycle]

    def generate_ideas(self, context: LoopContext) -> list[Idea]:
        focus_area = self.get_focus_area(context.iteration)
        
        if self.is_dry_run:
            LOGGER.info(f"[Dry Run] BrainstormEngine generating placeholder ideas for focus: {focus_area}")
            return [
                Idea(
                    title=f"Dry Run Idea {i}",
                    description=f"Placeholder description for {focus_area}",
                    focus_area=focus_area,
                    estimated_complexity="LOW",
                    estimated_impact="MEDIUM",
                    files_likely_affected=["src/apex/main.py"],
                    test_strategy="pytest"
                ) for i in range(1, 6)
            ]

        # Circuit breaker: skip LLM if provider is known-broken
        if _llm_is_broken():
            LOGGER.info("LLM circuit breaker active — using fallback ideas")
            from loop_modules.fallback_catalog import fallback_ideas
            return fallback_ideas(focus_area, context.iteration)

        from apex.core.config import get_settings
        from loop_modules.fallback_catalog import fallback_ideas
        from apex.core.llm_routing import llm_error_disables_route

        settings = get_settings()
        client = settings.get_llm_client()
        if not client:
            LOGGER.warning("No LLM client — using deterministic fallback ideas")
            return fallback_ideas(focus_area, context.iteration)

        prompt = f"""You are the master brain of the MarketMind x APEX autonomous loop.
Current Iteration: {context.iteration}
Focus Area: {focus_area}
Recent Ideas: {json.dumps(context.recent_ideas)}
Test Pass Rate: {context.test_pass_rate}
Backtest Metrics: {json.dumps(context.backtest_metrics)}
Recently Changed Files: {json.dumps(context.changed_files)}
Compact Summary of Previous Epochs: {context.compact_summary}

Generate exactly 5 distinct improvement ideas for the codebase based on the Focus Area.
Return ONLY valid JSON in the exact format:
[
  {{
    "title": "Short descriptive title",
    "description": "Detailed explanation of the change",
    "estimated_complexity": "LOW" | "MEDIUM" | "HIGH",
    "estimated_impact": "LOW" | "MEDIUM" | "HIGH",
    "files_likely_affected": ["list/of/files.py"],
    "test_strategy": "How this should be tested"
  }},
  ...
]
"""
        try:
            response = client.chat.completions.create(
                model=getattr(settings, "llm_model", "llama3.2:3b"),
                messages=[
                    {"role": "system", "content": "You are a quantitative software engineer generating strictly typed JSON arrays."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2048,
                temperature=0.7
            )
            raw = response.choices[0].message.content or "[]"
            # Extract JSON block if surrounded by markdown fences
            if "```" in raw:
                lines = raw.split("```")
                for block in lines:
                    if block.strip().startswith("[") or block.strip().startswith("{"):
                        raw = block
                        if raw.startswith("json"):
                            raw = raw[4:]
                        break

            parsed = json.loads(raw.strip())
            ideas = []
            for item in parsed:
                ideas.append(Idea(
                    title=item.get("title", "Untitled"),
                    description=item.get("description", ""),
                    focus_area=focus_area,
                    estimated_complexity=item.get("estimated_complexity", "MEDIUM"),
                    estimated_impact=item.get("estimated_impact", "MEDIUM"),
                    files_likely_affected=item.get("files_likely_affected", []),
                    test_strategy=item.get("test_strategy", "pytest")
                ))
            if not ideas:
                raise ValueError("Parsed JSON resulted in empty ideas list")
            return ideas[:5]
        except Exception as e:
            LOGGER.error(f"BrainstormEngine failed: {e}")
            # Engage circuit breaker for permanent auth/permission errors
            if llm_error_disables_route(e):
                _mark_llm_broken()

            LOGGER.warning("Using deterministic fallback ideas (LLM unavailable)")
            return fallback_ideas(focus_area, context.iteration)
