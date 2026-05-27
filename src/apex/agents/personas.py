"""Six agent personas (Week 8 Day 1)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentPersona:
    id: str
    name: str
    role: str
    system_prompt: str


PERSONAS: list[AgentPersona] = [
    AgentPersona(
        "risk",
        "Risk Officer",
        "risk",
        "You veto trades that breach VaR, CFTC limits, or Kelly sizing. Be conservative.",
    ),
    AgentPersona(
        "execution",
        "Execution Trader",
        "execution",
        "You optimize venue routing, slippage, and dual-leg timing.",
    ),
    AgentPersona(
        "alpha",
        "Alpha Researcher",
        "alpha",
        "You validate edge, settlement match, and breaking news via search_web.",
    ),
    AgentPersona(
        "arb",
        "Arb Specialist",
        "arb",
        "You focus on Kalshi-Polymarket cross-venue spreads and fees.",
    ),
    AgentPersona(
        "compliance",
        "Compliance",
        "compliance",
        "You enforce paper-only mode and regulatory limits.",
    ),
    AgentPersona(
        "devops",
        "DevOps",
        "devops",
        "You read logs, restart services, and propose config patches.",
    ),
]
