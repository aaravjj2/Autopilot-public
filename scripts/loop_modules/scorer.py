from __future__ import annotations

import logging

from loop_modules.models import Idea, LoopContext
from loop_modules.brainstorm import BrainstormEngine

LOGGER = logging.getLogger(__name__)

class IdeaScorer:
    def __init__(self, is_dry_run: bool = False):
        self.is_dry_run = is_dry_run

    def score_ideas(self, ideas: list[Idea], context: LoopContext) -> Idea:
        recent_titles = [item.get("idea", "") for item in context.recent_ideas]
        
        best_idea = None
        best_score = -1.0
        
        LOGGER.info("--- Idea Scoring Table ---")
        
        for idx, idea in enumerate(ideas):
            # Impact mapping
            impact_map = {"HIGH": 3.0, "MEDIUM": 2.0, "LOW": 1.0}
            impact_score = impact_map.get(idea.estimated_impact.upper(), 2.0)
            
            # Complexity mapping
            comp_map = {"HIGH": 0.5, "MEDIUM": 0.8, "LOW": 1.0}
            complexity_penalty = comp_map.get(idea.estimated_complexity.upper(), 0.8)
            
            # Novelty mapping
            novelty_score = 1.0 if idea.title not in recent_titles else 0.1
            
            final_score = impact_score * complexity_penalty * novelty_score
            
            LOGGER.info(f"Idea {idx+1}: {idea.title}")
            LOGGER.info(f"  Score: {final_score:.2f} (Impact: {impact_score}, Comp: {complexity_penalty}, Novelty: {novelty_score})")
            
            if final_score > best_score and novelty_score > 0.1:
                best_score = final_score
                best_idea = idea
                
        # If all 5 ideas were recently done (novelty 0.1 for all), regenerate
        if not best_idea:
            LOGGER.warning("All ideas were recent/stale. Regenerating...")
            engine = BrainstormEngine(is_dry_run=self.is_dry_run)
            new_ideas = engine.generate_ideas(context)
            # Try again (prevent infinite loop by taking the first this time, even if low score)
            return new_ideas[0]
            
        return best_idea
