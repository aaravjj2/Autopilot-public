"""Multi-agent vote consensus (Week 8 Day 2)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from apex.agents.personas import PERSONAS


@dataclass
class AgentVote:
    agent_id: str
    approve: bool
    confidence: float
    reason: str


@dataclass
class ConsensusResult:
    approved: bool
    votes: list[AgentVote] = field(default_factory=list)
    weighted_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "approved": self.approved,
            "weighted_score": self.weighted_score,
            "votes": [
                {
                    "agent_id": v.agent_id,
                    "approve": v.approve,
                    "confidence": v.confidence,
                    "reason": v.reason,
                }
                for v in self.votes
            ],
        }


class ConsensusEngine:
    """Simple weighted vote — replace with instructor/LLM in production."""

    WEIGHTS = {
        "risk": 2.0,
        "compliance": 2.0,
        "execution": 1.0,
        "alpha": 1.5,
        "arb": 1.5,
        "devops": 0.5,
    }

    def evaluate(self, proposal: dict[str, Any]) -> ConsensusResult:
        edge = float(proposal.get("net_edge") or 0)
        settlement = float(proposal.get("settlement_match_score") or 0.5)
        votes: list[AgentVote] = []

        for persona in PERSONAS:
            if persona.id == "risk":
                ok = edge >= 0.03 and settlement >= 0.45
                votes.append(
                    AgentVote(persona.id, ok, 0.8 if ok else 0.3, "VaR/settlement gate")
                )
            elif persona.id == "compliance":
                votes.append(AgentVote(persona.id, True, 1.0, "paper mode OK"))
            elif persona.id == "alpha":
                ok = edge >= 0.04
                votes.append(AgentVote(persona.id, ok, 0.7, "edge quality"))
            else:
                votes.append(
                    AgentVote(persona.id, edge >= 0.035, 0.6, f"{persona.role} review")
                )

        score = 0.0
        total_w = 0.0
        for v in votes:
            w = self.WEIGHTS.get(v.agent_id, 1.0)
            score += w * (v.confidence if v.approve else 0.0)
            total_w += w
        weighted = score / total_w if total_w > 0 else 0.0
        return ConsensusResult(
            approved=weighted >= 0.55,
            votes=votes,
            weighted_score=round(weighted, 4),
        )
