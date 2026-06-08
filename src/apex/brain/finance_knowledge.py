"""Curated, high-level finance + prediction-market strategy knowledge base.

This module is the "training data" for the autopilot brain. Rather than
fine-tuning a model (not available via a plain API key), we inject a compact,
high-signal corpus of institutional trading strategy, risk discipline, and
prediction-market arbitrage doctrine as system context. The corpus is
versioned and retrievable so the brain reasons from a consistent, auditable
body of knowledge.

Design goals:
- Every card is self-contained, factual, and actionable.
- Categories enable lightweight keyword retrieval (cheap RAG without a vector
  store) so prompts stay within token budgets.
- Content reflects the APEX domain: cross-venue prediction-market arbitrage
  (Kalshi/Polymarket), Kelly sizing, settlement risk, and disciplined paper
  execution.
"""

from __future__ import annotations

from dataclasses import dataclass, field

KNOWLEDGE_VERSION = "2026.05.2"


@dataclass(frozen=True)
class KnowledgeCard:
    """One atomic, retrievable unit of strategy knowledge."""

    id: str
    title: str
    category: str
    content: str
    tags: tuple[str, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# The corpus. Keep cards dense and decision-relevant.
# ---------------------------------------------------------------------------
KNOWLEDGE: tuple[KnowledgeCard, ...] = (
    KnowledgeCard(
        id="arb-core",
        title="Cross-venue prediction-market arbitrage",
        category="arbitrage",
        tags=("arbitrage", "kalshi", "polymarket", "edge", "spread"),
        content=(
            "A two-leg arbitrage buys YES on the cheaper venue and the complementary "
            "NO (or opposing YES) on the other so the combined cost of a guaranteed "
            "$1 payoff is < $1. Net edge = 1 - (kalshi_yes_ask + poly_no_ask) after "
            "fees and slippage. Only act when the SAME underlying event resolves on "
            "BOTH venues with identical settlement criteria; otherwise it is not an "
            "arbitrage, it is correlated directional risk. Edge must survive fees, "
            "the bid/ask you can actually fill (VWAP, not top-of-book), and "
            "settlement timing differences."
        ),
    ),
    KnowledgeCard(
        id="settlement-risk",
        title="Settlement-criteria risk is the #1 killer of fake arbs",
        category="risk",
        tags=("settlement", "risk", "resolution", "match"),
        content=(
            "Two markets can look identical by title yet resolve differently (source "
            "of truth, cutoff time, rounding, 'by end of year' vs 'by Dec 31 23:59 "
            "ET', tie/void handling). Require a high settlement_match_score and "
            "minimal settlement_flags before sizing. When in doubt, treat a "
            "title-only match as NOT arbitrageable. A 5% edge with mismatched "
            "settlement is a coin flip dressed as free money."
        ),
    ),
    KnowledgeCard(
        id="kelly",
        title="Fractional Kelly sizing under model uncertainty",
        category="sizing",
        tags=("kelly", "sizing", "bankroll", "position"),
        content=(
            "Full Kelly fraction f* = edge / odds maximizes long-run log growth but "
            "is too aggressive given estimation error. Use fractional Kelly "
            "(0.1-0.25x) to cut variance and survive model error and regime change. "
            "Cap any single position by bankroll % and per-venue exposure. Liquidity "
            "caps the trade before Kelly does: never size above what the thinner leg "
            "can fill near the quoted price."
        ),
    ),
    KnowledgeCard(
        id="liquidity",
        title="Liquidity and executable edge",
        category="execution",
        tags=("liquidity", "volume", "vwap", "slippage", "execution"),
        content=(
            "Quoted edge != realized edge. Size against the thinner leg's depth and "
            "compute the VWAP fill across the book, not the top quote. Thin markets "
            "(< a few thousand USD 24h volume) move on your own order and often have "
            "stale quotes. Prefer fewer, higher-quality, liquid opportunities over "
            "many thin ones. Min-leg volume is a hard gate, not a preference."
        ),
    ),
    KnowledgeCard(
        id="ranking",
        title="Ranking opportunities for limited capital",
        category="execution",
        tags=("ranking", "score", "edge", "priority"),
        content=(
            "With a finite per-cycle trade budget, rank by a composite execution "
            "score, not raw edge: net_edge weighted with settlement confidence, "
            "min-leg liquidity, executable VWAP edge, minus a penalty per settlement "
            "flag. Allocate the budget top-down through opportunities that clear the "
            "quality gate. Raw-edge-only ranking systematically selects thin, "
            "mis-settled traps."
        ),
    ),
    KnowledgeCard(
        id="risk-gates",
        title="Pre-trade risk gates (defense in depth)",
        category="risk",
        tags=("risk", "gate", "limits", "drawdown", "paper"),
        content=(
            "Enforce layered gates before any order: paper-mode required, min net "
            "edge, min settlement score, min leg volume, max settlement flags, "
            "per-position and per-venue exposure caps, and a daily loss limit that "
            "halts trading when breached. Gates fail closed: a missing or ambiguous "
            "signal blocks the trade. Risk checks run BEFORE sizing and submission, "
            "never after."
        ),
    ),
    KnowledgeCard(
        id="mean-reversion",
        title="Mean reversion vs momentum regimes",
        category="strategy",
        tags=("mean-reversion", "momentum", "regime", "equity"),
        content=(
            "Short-horizon prices often mean-revert; medium-horizon trends persist. "
            "Identify the regime before choosing a tactic: fade extremes in "
            "range-bound, low-volatility regimes; follow trends in expanding-"
            "volatility, high-ADX regimes. Mis-applying mean reversion in a strong "
            "trend produces serial losses. Use IV rank and realized/implied vol to "
            "infer the regime."
        ),
    ),
    KnowledgeCard(
        id="event-driven",
        title="Event-driven and catalyst trading",
        category="strategy",
        tags=("event", "catalyst", "earnings", "blackout"),
        content=(
            "Known catalysts (earnings, macro prints, elections, sports outcomes) "
            "concentrate variance. Respect earnings blackout windows for directional "
            "equity. For prediction markets, catalysts are the resolution itself: "
            "edge decays as resolution nears and information arrives. Avoid holding "
            "mis-settled legs across the catalyst."
        ),
    ),
    KnowledgeCard(
        id="market-making",
        title="Market-making and adverse selection",
        category="strategy",
        tags=("market-making", "spread", "inventory", "adverse-selection"),
        content=(
            "Providing liquidity earns the spread but exposes you to adverse "
            "selection: informed flow picks you off. Manage inventory toward neutral, "
            "widen quotes with volatility and uncertainty, and skew quotes to offload "
            "unwanted inventory. In prediction markets, a sudden one-sided sweep "
            "usually signals new information; pull quotes rather than catch the knife."
        ),
    ),
    KnowledgeCard(
        id="var",
        title="Portfolio risk: VaR, correlation, and tail hedging",
        category="risk",
        tags=("var", "monte-carlo", "correlation", "tail", "portfolio"),
        content=(
            "Position-level limits are necessary but insufficient; correlated "
            "positions aggregate into portfolio tail risk. Use VaR / Monte-Carlo to "
            "estimate loss at a confidence level and stress-test correlated shocks. "
            "Diversify across uncorrelated event clusters. A book of '10 independent "
            "5% edges' is far safer than one '50% edge' concentrated bet."
        ),
    ),
    KnowledgeCard(
        id="costs",
        title="Fees, funding, and the true cost of a round trip",
        category="execution",
        tags=("fees", "costs", "funding", "net"),
        content=(
            "Always reason in net terms. Subtract venue fees (taker/maker), "
            "withdrawal/settlement costs, and the spread you cross on BOTH legs. A "
            "gross 4% spread can be a negative net edge after two taker fees and "
            "slippage. If net edge after realistic costs is below the configured "
            "floor, do not trade."
        ),
    ),
    KnowledgeCard(
        id="discipline",
        title="Process discipline and paper-trading integrity",
        category="discipline",
        tags=("discipline", "paper", "process", "audit"),
        content=(
            "Edge comes from process, not prediction. Log every decision with its "
            "rationale and the gates it passed/failed for auditability. In paper "
            "mode, never simulate fills better than the live book would give. "
            "Consistency and survivability beat occasional brilliance; the goal is "
            "positive expectancy compounded without ruin."
        ),
    ),
    KnowledgeCard(
        id="quant-math",
        title="Quantitative foundations (APEX quant engine)",
        category="math",
        tags=("math", "kelly", "edge", "fee", "score", "formula"),
        content=(
            "Two-leg locked payoff: gross = 1 - (kalshi_yes_ask + poly_no_ask). "
            "Kalshi fee on YES win: fee = 0.07 * (1 - yes_ask). Net edge = gross - fee. "
            "Binary Kelly: cost = yes_ask + no_ask, b = (1-cost)/cost, "
            "f* = (p*b - (1-p))/b; trade f = KELLY_ALPHA * f* (default alpha=0.25). "
            "Size cap = min(bankroll*f, 0.10 * min_leg_volume). Execution score ranks "
            "opportunities: edge + 0.25*settlement + 0.15*log1p(min_vol)/15 + vwap_bonus "
            "- 0.05*flags. EXECUTE requires gates pass, score >= 0.08, net >= 3%, "
            "settlement >= 0.80, no flags, min-leg vol >= 5x gate."
        ),
    ),
)

_CARD_BY_ID = {c.id: c for c in KNOWLEDGE}


def all_cards() -> tuple[KnowledgeCard, ...]:
    return KNOWLEDGE


def card(card_id: str) -> KnowledgeCard | None:
    return _CARD_BY_ID.get(card_id)


def categories() -> set[str]:
    return {c.category for c in KNOWLEDGE}


def retrieve(query: str, *, limit: int = 6) -> list[KnowledgeCard]:
    """Cheap keyword retrieval: rank cards by tag/title/content term overlap.

    Avoids a vector store while keeping prompts focused. Deterministic and
    fully offline, which keeps the brain testable without network access.
    """
    terms = {t for t in _tokenize(query) if len(t) > 2}
    if not terms:
        return list(KNOWLEDGE[:limit])
    scored: list[tuple[float, KnowledgeCard]] = []
    for c in KNOWLEDGE:
        hay_tags = {t.lower() for t in c.tags}
        hay_text = set(_tokenize(f"{c.title} {c.category} {c.content}"))
        score = 3.0 * len(terms & hay_tags) + 1.0 * len(terms & hay_text)
        if score > 0:
            scored.append((score, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    if not scored:
        return list(KNOWLEDGE[:limit])
    return [c for _, c in scored[:limit]]


def _tokenize(text: str) -> list[str]:
    out: list[str] = []
    word = []
    for ch in text.lower():
        if ch.isalnum() or ch == "-":
            word.append(ch)
        elif word:
            out.append("".join(word))
            word = []
    if word:
        out.append("".join(word))
    return out


CORE_DOCTRINE = (
    "You are APEX, an institutional-grade autonomous trading analyst for "
    "cross-venue prediction-market arbitrage (Kalshi and Polymarket) and "
    "supporting equity/options context. You operate strictly in PAPER mode. "
    "You are disciplined, risk-first, and quantitative. You never invent "
    "liquidity or settlement equivalence. You prefer fewer high-quality, "
    "liquid, well-settled opportunities over many thin ones. You reason in NET "
    "terms after fees and slippage. When evidence is weak or ambiguous, you "
    "recommend SKIP. You explain the specific risk that would invalidate the "
    "trade."
)


def build_system_prompt(query: str | None = None, *, max_cards: int = 8) -> str:
    """Compose the brain's system prompt from doctrine + relevant knowledge."""
    cards = retrieve(query, limit=max_cards) if query else list(KNOWLEDGE[:max_cards])
    parts = [CORE_DOCTRINE, "", f"STRATEGY KNOWLEDGE (v{KNOWLEDGE_VERSION}):"]
    for c in cards:
        parts.append(f"- [{c.category}] {c.title}: {c.content}")
    return "\n".join(parts)
