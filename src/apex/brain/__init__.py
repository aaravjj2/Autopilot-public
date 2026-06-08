"""APEX autopilot brain: an LLM-backed finance reasoner with a curated
high-level finance/prediction-market strategy knowledge base.

The brain is provider-agnostic (routes through ``Settings.get_llm_client``)
and degrades gracefully to the quantitative engine when no LLM route is
live, so the autopilot never hard-fails on the model layer.
"""

from __future__ import annotations

from apex.brain.finance_brain import BrainVerdict, FinanceBrain, get_brain

__all__ = ["BrainVerdict", "FinanceBrain", "get_brain"]
