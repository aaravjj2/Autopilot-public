---
name: thesis-card
description: >
  Use this skill to implement the ArbAnalystPanel (4-sub-agent Claude streaming thesis),
  the FastAPI SSE endpoint /api/arb/{id}/thesis, and the Next.js ThesisCard component.
  Trigger when building the AI thesis streaming pipeline, the multi-agent panel for arb
  analysis, or any SSE consumer on the frontend.
compatibility: Antigravity CLI (agy), Claude Code, Gemini CLI
---

# Thesis Card Streaming Skill

## ArbThesis Dataclass

```python
# src/apex/domain/models.py (add)
@dataclass
class ArbThesis:
    settlement_verdict: str         # "SAFE" | "CAUTION" | "BLOCK"
    settlement_explanation: str     # why the resolution criteria align or diverge
    divergence_reason: str          # structural explanation (Kalshi vs Poly audience)
    bull_case: str                  # why the arb converges
    bear_case: str                  # what could go wrong
    recommended_leg: str            # "KALSHI_YES + POLY_NO" | "POLY_YES + KALSHI_NO" | "SKIP"
    net_edge_estimate: float        # after fees
    annualised_sharpe: float | None
    confidence: str                 # "HIGH" | "MEDIUM" | "LOW"
    risk_flags: list[str]           # from SettlementAuditor + EdgeCalculator
    one_liner: str                  # ≤ 20 words for the arb-radar table
```

---

## ArbAnalystPanel — 4-Sub-Agent Sequence

```python
# src/apex/layers/l2/arb_analyst_panel.py
from __future__ import annotations
import anthropic
import json
from dataclasses import dataclass
from apex.core.config import Settings
from apex.core.logging import get_logger
from apex.domain.models import ArbOpportunity, ArbThesis

LOGGER = get_logger(__name__)
MODEL  = "claude-sonnet-4-20250514"

SYSTEM_PROMPT = """\
You are a four-agent panel analysing a cross-platform prediction market arbitrage opportunity.
You will run four internal reasoning agents in sequence and output a single JSON object.

Agent 1 — SettlementAuditor:
  Analyse whether the resolution criteria on Kalshi and Polymarket are compatible.
  Output: settlement_verdict (SAFE/CAUTION/BLOCK), settlement_explanation (1–2 sentences)

Agent 2 — PlatformDemographer:
  Explain the structural, demographic, and information-environment reasons why
  Kalshi and Polymarket users might price this event differently.
  Output: divergence_reason (2–3 sentences)

Agent 3 — EdgeCalculator:
  Calculate the true net edge after fees (Kalshi: 7% of winnings, Poly: 0%).
  State which leg is the better buy.
  Output: bull_case, bear_case, recommended_leg, net_edge_estimate, annualised_sharpe (if resolution date known)

Agent 4 — Adversarial (Dexter-style):
  What is the strongest argument that this arb will NOT converge?
  What would cause both legs to lose?
  Output: bear_case extension, risk_flags (list), confidence (HIGH/MEDIUM/LOW)

After all four agents, synthesise:
  one_liner: ≤ 20 words summarising the opportunity

RESPOND ONLY WITH A SINGLE JSON OBJECT. No preamble, no markdown fences.
"""

@dataclass
class ArbAnalystPanel:
    settings: Settings

    async def evaluate(self, opp: ArbOpportunity) -> ArbThesis:
        """Run all 4 sub-agents and return structured ArbThesis."""
        client = anthropic.AsyncAnthropic(api_key=self.settings.anthropic_api_key)

        user_content = f"""
OPPORTUNITY ID: {opp.id}
KALSHI TICKER: {opp.kalshi_ticker}
KALSHI TITLE: {opp.kalshi_title}
POLYMARKET QUESTION: {opp.poly_title}

KALSHI YES ASK: ${opp.kalshi_yes_ask:.3f}
POLY NO ASK:    ${opp.poly_no_ask:.3f}
GROSS SPREAD:   ${opp.gross_spread:.3f}
NET EDGE (after 7% Kalshi fee): ${opp.net_edge:.3f}

SETTLEMENT PRE-CHECK:
  match_score: {opp.settlement_match_score}
  flags: {opp.settlement_flags}

VOLUME: Kalshi 24h=${opp.volume_kalshi:,.0f}  Poly 24h=${opp.volume_poly:,.0f}

Run all four agents and return the JSON thesis.
"""
        full_text = ""
        async with client.messages.stream(
            model=MODEL,
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        ) as stream:
            async for chunk in stream.text_stream:
                full_text += chunk

        return self._parse_thesis(full_text)

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
            return ArbThesis(
                settlement_verdict="CAUTION",
                settlement_explanation="Parse error",
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
```

---

## FastAPI SSE Endpoint

```python
# src/apex/integrations/thesis_service.py
from __future__ import annotations
import asyncio
import anthropic
import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from apex.core.config import get_settings
from apex.core.logging import get_logger
from apex.repositories.sqlite_store import SQLiteStore

LOGGER = get_logger(__name__)
router = APIRouter()
MODEL  = "claude-sonnet-4-20250514"

SYSTEM_PROMPT = """..."""  # same as ArbAnalystPanel above

@router.get("/api/arb/{arb_id}/thesis")
async def stream_arb_thesis(arb_id: str):
    settings = get_settings()
    store    = SQLiteStore(settings.sqlite_path)
    opp      = store.get_arb_opportunity(arb_id)
    if opp is None:
        raise HTTPException(status_code=404, detail="Arb opportunity not found")

    async def event_generator():
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        user_content = f"Analyse arb opportunity: {json.dumps(vars(opp), default=str)}"
        async with client.messages.stream(
            model=MODEL,
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        ) as stream:
            async for chunk in stream.text_stream:
                yield f"data: {json.dumps({'token': chunk})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
```

Register in `autopilot-local/backend/main.py`:
```python
from thesis_service import router as thesis_router
app.include_router(thesis_router)
```

---

## Next.js ThesisCard Component

```tsx
// autopilot-local/frontend/components/ThesisCard.tsx
"use client";

import { useEffect, useRef, useState } from "react";

interface ThesisCardProps {
  arbId: string;
  autoStart?: boolean;
}

export function ThesisCard({ arbId, autoStart = false }: ThesisCardProps) {
  const [text, setText] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [parsed, setParsed] = useState<Record<string, unknown> | null>(null);
  const esRef = useRef<EventSource | null>(null);

  const startStream = () => {
    if (esRef.current) esRef.current.close();
    setText("");
    setParsed(null);
    setStreaming(true);
    const es = new EventSource(`/api/arb/${arbId}/thesis`);
    esRef.current = es;

    es.onmessage = (e) => {
      if (e.data === "[DONE]") {
        setStreaming(false);
        es.close();
        // Try to parse final JSON
        try {
          const full = text + (JSON.parse(e.data)?.token ?? "");
          setParsed(JSON.parse(full));
        } catch {}
        return;
      }
      const chunk = JSON.parse(e.data).token ?? "";
      setText((prev) => prev + chunk);
    };

    es.onerror = () => {
      setStreaming(false);
      es.close();
    };
  };

  useEffect(() => {
    if (autoStart) startStream();
    return () => esRef.current?.close();
  }, [arbId]);

  // Try to parse accumulated JSON progressively
  useEffect(() => {
    try { setParsed(JSON.parse(text)); } catch {}
  }, [text]);

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-800">AI Thesis</h3>
        <button
          onClick={startStream}
          disabled={streaming}
          className="text-xs px-3 py-1 rounded bg-teal-600 text-white disabled:opacity-50"
        >
          {streaming ? "Generating…" : "Generate"}
        </button>
      </div>

      {parsed ? (
        <div className="space-y-2 text-sm">
          <div className={`px-2 py-1 rounded text-xs font-semibold
            ${parsed.settlement_verdict === "SAFE" ? "bg-green-100 text-green-700" :
              parsed.settlement_verdict === "CAUTION" ? "bg-yellow-100 text-yellow-700" :
              "bg-red-100 text-red-700"}`}>
            Settlement: {String(parsed.settlement_verdict)} — {String(parsed.settlement_explanation)}
          </div>
          <details>
            <summary className="cursor-pointer text-gray-600 font-medium">
              Divergence Reason
            </summary>
            <p className="mt-1 text-gray-700">{String(parsed.divergence_reason)}</p>
          </details>
          <details>
            <summary className="cursor-pointer text-green-600 font-medium">Bull Case</summary>
            <p className="mt-1 text-gray-700">{String(parsed.bull_case)}</p>
          </details>
          <details>
            <summary className="cursor-pointer text-red-600 font-medium">Bear Case</summary>
            <p className="mt-1 text-gray-700">{String(parsed.bear_case)}</p>
          </details>
          <div className="text-xs text-gray-500">
            <strong>Recommended:</strong> {String(parsed.recommended_leg)} |{" "}
            <strong>Edge:</strong> ${Number(parsed.net_edge_estimate).toFixed(3)} |{" "}
            <strong>Confidence:</strong> {String(parsed.confidence)}
          </div>
          {Array.isArray(parsed.risk_flags) && parsed.risk_flags.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {(parsed.risk_flags as string[]).map((f) => (
                <span key={f} className="text-xs bg-orange-100 text-orange-700 px-2 py-0.5 rounded">
                  {f}
                </span>
              ))}
            </div>
          )}
          <p className="italic text-gray-500 text-xs">{String(parsed.one_liner)}</p>
        </div>
      ) : text ? (
        <pre className="text-xs text-gray-600 whitespace-pre-wrap font-mono bg-gray-50 p-2 rounded">
          {text}
          {streaming && <span className="animate-pulse">▌</span>}
        </pre>
      ) : null}
    </div>
  );
}
```

---

## Critical Notes

- `ThesisCard` **must** have `"use client"` — SSE EventSource is browser-only
- Never use `fetch()` for SSE — use `new EventSource(url)`
- The FastAPI backend must add CORS headers if frontend is on a different port
- `stream=True` on Anthropic SDK requires `AsyncAnthropic`, not `Anthropic`
