"""Final decision engine with Kelly sizing and hard guards."""

from __future__ import annotations

from features.market_features import compute_edge, is_liquid_enough, kelly_fraction


def make_decision(agent_response: dict, context: dict) -> dict:
    agent_prob = float(agent_response["estimated_probability"])
    market_prob = float(context["implied_prob"])
    edge = compute_edge(agent_prob, market_prob)

    action = agent_response.get("action", "skip")
    if abs(edge) < 0.05:
        action = "skip"
    if not is_liquid_enough(context):
        action = "skip"

    kf = kelly_fraction(edge, agent_prob=agent_prob) if action != "skip" else 0.0
    stake = min(float(context["bankroll"]) * kf, float(context["max_stake"]))
    stake = max(0.0, stake)

    return {
        "action": action,
        "stake": round(stake, 2),
        "kelly_fraction": round(kf, 4),
        "edge": round(edge, 4),
        "agent_estimated_prob": agent_prob,
        "market_implied_prob": market_prob,
        "reasoning": agent_response.get("reasoning", ""),
        "key_factors": agent_response.get("key_factors", []),
        "red_flags": agent_response.get("red_flags", []),
    }
