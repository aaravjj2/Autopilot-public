from __future__ import annotations

import json
import asyncio
from dataclasses import dataclass
from apex.core.config import Settings
from apex.core.logging import get_logger
from apex.domain.models import ArbOpportunity, ArbThesis

LOGGER = get_logger(__name__)
MODEL  = "llama-3.1-70b-versatile" # Default for groq, will be overridden by client default if needed

SYSTEM_PROMPT_AGENT_1 = """\
You are Agent 1 — SettlementAuditor:
Analyse whether the resolution criteria on Kalshi and Polymarket are compatible.
Output: JSON object with keys: settlement_verdict (SAFE/CAUTION/BLOCK), settlement_explanation (1–2 sentences).
"""

SYSTEM_PROMPT_AGENT_2 = """\
You are Agent 2 — PlatformDemographer:
Explain the structural, demographic, and information-environment reasons why Kalshi and Polymarket users might price this event differently.
Output: JSON object with key: divergence_reason (2–3 sentences).
"""

SYSTEM_PROMPT_AGENT_3 = """\
You are Agent 3 — EdgeCalculator:
Calculate the true net edge after fees (Kalshi: 7% of winnings, Poly: 0%). State which leg is the better buy.
Output: JSON object with keys: bull_case, bear_case, recommended_leg, net_edge_estimate (float), annualised_sharpe (float or null).
"""

SYSTEM_PROMPT_AGENT_4 = """\
You are Agent 4 — Adversarial (Dexter-style):
What is the strongest argument that this arb will NOT converge? What would cause both legs to lose?
Output: JSON object with keys: bear_case_extension (string), risk_flags (list of strings), confidence (HIGH/MEDIUM/LOW).
"""

SYSTEM_PROMPT_SYNTHESIS = """\
You are the Lead Analyst.
Synthesise the opportunity into a JSON object with key: one_liner (≤ 20 words summarising the opportunity).
"""
@dataclass
class ArbAnalystPanel:
    settings: Settings

    async def evaluate(self, opp: ArbOpportunity) -> ArbThesis:
        """Run all 4 sub-agents in parallel and return structured ArbThesis."""
        if self.settings.demo_mode:
            return self._demo_thesis(opp)
        client = self.settings.get_llm_client()
        if client is None:
            return self._fallback_thesis(opp)
            
        from apex.repositories.sqlite_store import SQLiteStore
        store = SQLiteStore(self.settings.sqlite_path)
        past_trades = store.get_resolved_arb_opportunities(limit=5)
        past_trades_context = "\n=== RECENT RESOLVED ARB TRADES ===\n"
        for pt in past_trades:
            past_trades_context += f"- {pt.kalshi_title} vs {pt.poly_title} | Outcome: {pt.outcome} | PNL: ${pt.pnl}\n"

        user_content = f"""
OPPORTUNITY ID: {opp.id}
KALSHI TICKER: {opp.kalshi_ticker}
KALSHI TITLE: {opp.kalshi_title}
POLYMARKET QUESTION: {opp.poly_title}

KALSHI YES ASK: ${opp.kalshi_yes_ask:.3f}
POLY NO ASK:    ${opp.poly_no_ask:.3f}
GROSS SPREAD:   ${opp.gross_spread:.3f}
NET EDGE (after 7% Kalshi fee): ${opp.net_edge:.3f}

{past_trades_context}

SETTLEMENT PRE-CHECK:
  match_score: {opp.settlement_match_score}
  flags: {opp.settlement_flags}

VOLUME: Kalshi 24h=${opp.volume_kalshi:,.0f}  Poly 24h=${opp.volume_poly:,.0f}

Run all four agents and return the JSON thesis.
"""
        def _call_llm(prompt: str, extra_user_content: str = "") -> dict:
            try:
                response = client.chat.completions.create(
                    model=MODEL,
                    messages=[
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": user_content + extra_user_content}
                    ],
                    temperature=0.2,
                    max_tokens=800,
                    response_format={"type": "json_object"} if hasattr(client, "_base_url") else None
                )
                txt = response.choices[0].message.content or "{}"
                # try parsing to test validity
                return json.loads(txt.strip().lstrip("```json").rstrip("```").strip())
            except Exception as e:
                LOGGER.error("Agent call failed: %s", e)
                return {}

        agent_1_prompt = SYSTEM_PROMPT_AGENT_1
        failed_examples = store.get_failed_thesis_examples(limit=5)
        if failed_examples:
            agent_1_prompt += "\n\n=== CAUTIONARY EXAMPLES (Rated SAFE but resulted in LOSS) ===\n"
            for ex in failed_examples:
                agent_1_prompt += f"- Kalshi: '{ex.kalshi_title}' vs Poly: '{ex.poly_title}' -> PNL: ${ex.pnl}\n"

        phase1_results = await asyncio.gather(
            asyncio.to_thread(_call_llm, agent_1_prompt),
            asyncio.to_thread(_call_llm, SYSTEM_PROMPT_AGENT_2),
            asyncio.to_thread(_call_llm, SYSTEM_PROMPT_AGENT_3),
        )
        
        phase1_data = {}
        for r in phase1_results:
            phase1_data.update(r)
            
        extra_content = f"\n\nCOMBINED PHASE 1 OUTPUTS:\n{json.dumps(phase1_data, indent=2)}\n"

        phase2_results = await asyncio.gather(
            asyncio.to_thread(_call_llm, SYSTEM_PROMPT_AGENT_4, extra_content),
            asyncio.to_thread(_call_llm, SYSTEM_PROMPT_SYNTHESIS, extra_content),
        )
        
        merged_data = dict(phase1_data)
        for r in phase2_results:
            merged_data.update(r)

        return self._parse_thesis_data(merged_data)

    def _parse_thesis_data(self, data: dict) -> ArbThesis:
        try:
            return ArbThesis(
                settlement_verdict=data.get("settlement_verdict", "CAUTION"),
                settlement_explanation=data.get("settlement_explanation", ""),
                divergence_reason=data.get("divergence_reason", ""),
                bull_case=data.get("bull_case", ""),
                bear_case=data.get("bear_case_extension", data.get("bear_case", "")),
                recommended_leg=data.get("recommended_leg", "SKIP"),
                net_edge_estimate=float(data.get("net_edge_estimate", 0)),
                annualised_sharpe=data.get("annualised_sharpe"),
                confidence=data.get("confidence", "LOW"),
                risk_flags=data.get("risk_flags", []),
                one_liner=data.get("one_liner", ""),
            )
        except Exception as e:
            LOGGER.error("Failed to parse ArbThesis from dict: %s", e)
            return self._fallback_thesis(None)

    def _parse_thesis(self, raw: str) -> ArbThesis:
        try:
            clean = raw.strip().lstrip("```json").rstrip("```").strip()
            data  = json.loads(clean)
            return ArbThesis(
                settlement_verdict=data.get("settlement_verdict", "CAUTION"),
                settlement_explanation=data.get("settlement_explanation", ""),
                divergence_reason=data.get("divergence_reason", ""),
                bull_case=data.get("bull_case", ""),
                bear_case=data.get("bear_case", ""),
                recommended_leg=data.get("recommended_leg", "SKIP"),
                net_edge_estimate=float(data.get("net_edge_estimate", 0)),
                annualised_sharpe=data.get("annualised_sharpe"),
                confidence=data.get("confidence", "LOW"),
                risk_flags=data.get("risk_flags", []),
                one_liner=data.get("one_liner", ""),
            )
        except Exception as e:
            LOGGER.error("Failed to parse ArbThesis JSON: %s | raw=%s", e, raw[:200])
            return self._fallback_thesis(None)

    def _demo_thesis(self, opp: ArbOpportunity) -> ArbThesis:
        verdict = "SAFE" if opp.settlement_match_score >= 0.75 else "CAUTION"
        if "BLOCK" in opp.settlement_flags:
            verdict = "BLOCK"
        return ArbThesis(
            arb_id=opp.id,
            settlement_verdict=verdict,
            settlement_explanation=(
                f"Demo settlement audit: match score {opp.settlement_match_score:.0%} "
                f"across Kalshi ({opp.kalshi_ticker}) and Polymarket."
            ),
            divergence_reason=(
                "Retail vs institutional participant mix differs by venue; "
                "demo mode uses seeded spreads without live LLM."
            ),
            bull_case=f"Net edge ${opp.net_edge:.3f} after Kalshi fee with ${opp.volume_kalshi:,.0f} Kalshi vol.",
            bear_case="Resolution wording or liquidity could erode edge before fill.",
            recommended_leg="BUY_KALSHI_YES_POLY_NO" if opp.net_edge >= 0.03 else "SKIP",
            net_edge_estimate=opp.net_edge,
            annualised_sharpe=1.2 if opp.net_edge >= 0.04 else 0.6,
            confidence="HIGH" if opp.net_edge >= 0.05 else "MEDIUM",
            risk_flags=list(opp.settlement_flags) or [],
            one_liner=f"{opp.kalshi_ticker}: {opp.net_edge * 100:.1f}% net edge (demo thesis)",
            llm_provider="demo",
        )

    def _fallback_thesis(self, opp: ArbOpportunity | None) -> ArbThesis:
        if opp is not None and self.settings.demo_mode:
            return self._demo_thesis(opp)
        return ArbThesis(
            settlement_verdict="CAUTION",
            settlement_explanation="Fallback/Parse error",
            divergence_reason="",
            bull_case="",
            bear_case="",
            recommended_leg="SKIP",
            net_edge_estimate=0.0,
            annualised_sharpe=None,
            confidence="LOW",
            risk_flags=["parse_error"],
            one_liner="Unable to generate thesis",
        )
