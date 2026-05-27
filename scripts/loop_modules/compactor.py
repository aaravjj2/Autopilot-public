from __future__ import annotations

import json
import logging
from pathlib import Path

from loop_modules.models import LoopState

LOGGER = logging.getLogger(__name__)

class LoopCompactor:
    def __init__(self, is_dry_run: bool = False):
        self.is_dry_run = is_dry_run
        self.workspace = Path("/home/aarav/Aarav/Autopilot")

    def compact(self, state: LoopState) -> str:
        if self.is_dry_run:
            return "Dry run compact summary."

        from apex.core.config import get_settings
        settings = get_settings()
        client = settings.get_llm_client()
        if not client:
            return state.last_compact_summary

        recent = state.idea_history[-10:] if len(state.idea_history) >= 10 else state.idea_history
        
        prompt = f"""You are the Loop Compactor.
Summarize the following 10 recent iterations into a dense, informative paragraph.
Focus on:
1. What was built and its outcome (SUCCESS/FAIL).
2. Key architectural decisions made.
3. Current capabilities vs what existed before.

Recent History:
{json.dumps(recent, indent=2)}

Previous Compact Summary:
{state.last_compact_summary}

Return ONLY the plain text summary paragraph.
"""
        try:
            res = client.chat.completions.create(
                model=getattr(settings, "llm_model", "llama3.2:3b"),
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500
            )
            summary = res.choices[0].message.content or ""
            
            # Save to disk
            path = self.workspace / "data" / "compacts" / f"compact_{state.current_iteration:04d}.md"
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(summary)
                
            return summary.strip()
        except Exception as e:
            LOGGER.error(f"Failed to compact state: {e}")
            return state.last_compact_summary
