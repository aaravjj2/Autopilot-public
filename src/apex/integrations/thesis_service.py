"""thesis_service.py — LLM-backed arb thesis generator.

Builds a structured ArbThesis from a detected ArbOpportunity using whichever
LLM client is available via ``settings.get_llm_client()``.

Priority: Groq → OpenRouter → Ollama (fallback, always available).
If *no* client can be initialised, returns a safe placeholder and never raises.
"""
from __future__ import annotations

import json
from typing import Any
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from apex.core.config import Settings, get_settings
from apex.core.logging import get_logger
from apex.domain.models import ArbOpportunity, ArbThesis

router = APIRouter()

LOGGER = get_logger(__name__)

# ---------------------------------------------------------------------------
# Domain model
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = (
    "You are a quantitative arbitrage analyst. "
    "Given a cross-platform prediction-market opportunity between Kalshi and Polymarket, "
    "produce a concise JSON thesis. "
    "Respond with ONLY valid JSON — no markdown fences, no preamble. "
    "Schema: {"
    "\"one_liner\": string, "
    "\"confidence\": float 0-1, "
    "\"bull_case\": string, "
    "\"bear_case\": string, "
    "\"recommended_action\": string, "
    "\"key_risks\": [string], "
    "\"settlement_notes\": string"
    "}"
)


def _build_user_prompt(opp: ArbOpportunity) -> str:
    # Implied prices derived from available fields
    kalshi_no_ask = 1.0 - opp.kalshi_yes_ask
    poly_yes_ask = 1.0 - opp.poly_no_ask
    return (
        f"Question: {opp.question}\n"
        f"Kalshi YES ask: {opp.kalshi_yes_ask:.4f}  "
        f"Kalshi NO ask: {kalshi_no_ask:.4f}\n"
        f"Polymarket YES implied: {poly_yes_ask:.4f}  "
        f"Polymarket NO implied: {opp.poly_no_ask:.4f}\n"
        f"Net edge (after fees): {opp.net_edge:.4f}\n"
        f"Kalshi 24h volume: {opp.volume_kalshi:,.0f}  "
        f"Polymarket 24h volume: {opp.volume_poly:,.0f}\n"
        f"Title match score: {opp.settlement_match_score:.2f}\n"
        "\nProduce the JSON thesis now."
    )


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------

def _parse_thesis_json(raw: str, arb_id: str, provider: str) -> ArbThesis:
    """Parse a raw LLM JSON string into an ArbThesis.  Never raises."""
    try:
        data: dict[str, Any] = json.loads(raw.strip())
        return ArbThesis(
            arb_id=arb_id,
            one_liner=str(data.get("one_liner", "")),
            confidence=str(data.get("confidence", "MEDIUM")),
            bull_case=str(data.get("bull_case", "")),
            bear_case=str(data.get("bear_case", "")),
            recommended_leg=str(data.get("recommended_action", "SKIP")),
            risk_flags=[str(r) for r in data.get("key_risks", [])],
            settlement_explanation=str(data.get("settlement_notes", "")),
            llm_provider=provider,
        )
    except Exception as exc:
        LOGGER.warning("_parse_thesis_json: failed to parse JSON from %s: %s", provider, exc)
        return _placeholder_thesis(arb_id, f"JSON parse error from {provider}: {exc}")


def _placeholder_thesis(arb_id: str, reason: str = "LLM unavailable — no API key configured") -> ArbThesis:
    return ArbThesis(
        arb_id=arb_id,
        one_liner=reason,
        confidence="LOW",
        bull_case="",
        bear_case="",
        recommended_leg="SKIP",
        risk_flags=["llm_error"],
        settlement_explanation=reason,
        llm_provider="none",
    )


# ---------------------------------------------------------------------------
# LLM call helpers
# ---------------------------------------------------------------------------


def _call_openai_compat(client: Any, user_prompt: str) -> str:
    """Call any OpenAI-compatible client (Groq, OpenRouter, Ollama) and return raw text."""

    # Determine a sensible model name — prefer a fast / cheap one if it's Ollama
    try:
        settings = get_settings()
        model = settings.ollama_model if hasattr(client, "_base_url") else settings.llm_model
    except Exception:
        model = "llama3.2:3b"

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=512,
        temperature=0.2,
    )
    return str(response.choices[0].message.content or "")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class ThesisService:
    """Generate structured LLM theses for arbitrage opportunities.

    Resolves the LLM client via ``settings.get_llm_client()`` on each call so
    that hot-reloaded settings (e.g. in tests) are respected.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    async def generate(self, opp: ArbOpportunity) -> ArbThesis:
        """Asynchronously generate an ArbThesis for *opp*.

        Returns a safe placeholder if no LLM client is available.  Never raises.
        """
        client = self._settings.get_llm_client()
        if client is None:
            LOGGER.warning(
                "ThesisService.generate: no LLM client — returning placeholder for arb %s",
                opp.id,
            )
            return _placeholder_thesis(opp.id)

        from apex.layers.l2.arb_analyst_panel import ArbAnalystPanel

        panel = ArbAnalystPanel(self._settings)
        thesis = await panel.evaluate(opp)
            
        thesis.arb_id = opp.id
        return thesis


@router.get("/api/arb/{arb_id}/thesis")
async def stream_arb_thesis(arb_id: str):
    settings = get_settings()
    from apex.repositories.sqlite_store import SQLiteStore
    store = SQLiteStore(settings.sqlite_path)
    opp_dict = store.get_arb_opportunity(arb_id)
    if not opp_dict:
        raise HTTPException(status_code=404, detail="Arb opportunity not found")

    async def event_generator():
        client = settings.get_llm_client()
        if client is None:
            yield f"data: {json.dumps({'token': 'Error: No LLM client configured.'})}\n\n"
            yield "data: [DONE]\n\n"
            return
            
        import asyncio
        from apex.domain.models import ArbOpportunity
        
        opp = ArbOpportunity(
            id=opp_dict["id"],
            kalshi_ticker=opp_dict["kalshi_ticker"],
            poly_market_id=opp_dict["poly_market_id"],
            question=opp_dict["question"],
            kalshi_title=opp_dict["kalshi_title"],
            poly_title=opp_dict["poly_title"],
            kalshi_yes_ask=opp_dict["kalshi_yes_ask"],
            poly_no_ask=opp_dict["poly_no_ask"],
            gross_spread=opp_dict["gross_spread"],
            net_edge=opp_dict["net_edge"],
            settlement_match_score=opp_dict["settlement_match_score"],
            settlement_flags=json.loads(opp_dict["settlement_flags"] or "[]"),
            volume_kalshi=opp_dict.get("volume_kalshi", 0.0),
            volume_poly=opp_dict.get("volume_poly", 0.0)
        )
        
        try:
            service = ThesisService(settings)
            thesis = await service.generate(opp)
            import dataclasses
            full_json_str = json.dumps(dataclasses.asdict(thesis), indent=2)
            
            # Send the result in chunks to simulate streaming
            chunk_size = 32
            for i in range(0, len(full_json_str), chunk_size):
                chunk = full_json_str[i:i+chunk_size]
                yield f"data: {json.dumps({'token': chunk})}\n\n"
                await asyncio.sleep(0.05)
                
        except Exception as e:
            LOGGER.error("Streaming LLM failed: %s", e)
            yield f"data: {json.dumps({'token': f'Error generating thesis: {e}'})}\n\n"
            
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
