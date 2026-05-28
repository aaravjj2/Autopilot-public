from __future__ import annotations

import json
import logging

from loop_modules.models import Idea, LoopContext

LOGGER = logging.getLogger(__name__)

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

        from apex.core.config import get_settings
        settings = get_settings()
        client = settings.get_llm_client()
        if not client:
            raise RuntimeError("No LLM client configured for BrainstormEngine")

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
            raise
