---
name: add-thesis-stream
description: >
  Adds the ArbAnalystPanel (4-sub-agent Claude streaming thesis) and wires it to a
  FastAPI SSE endpoint and Next.js ThesisCard component. Run this after /build-arb-layer.
slash_command: /add-thesis-stream
---

# /add-thesis-stream Workflow

Add streaming AI thesis generation to MarketMind.
**Prerequisite:** `/build-arb-layer` must have been run first.

---

## Step 1 — ArbAnalystPanel backend

**Agent:** Multi-Agent Panel Specialist (L2)
**Read skill:** `thesis-card`

Create `src/apex/layers/l2/arb_analyst_panel.py`:
- `ArbAnalystPanel` dataclass with `evaluate(opp: ArbOpportunity) -> ArbThesis`
- 4-agent system prompt (SettlementAuditor → PlatformDemographer → EdgeCalculator → Adversarial)
- Async streaming via `anthropic.AsyncAnthropic().messages.stream()`
- JSON parsing with `_parse_thesis()` fallback

Use model: `claude-sonnet-4-20250514`, max_tokens: 1500.

---

## Step 2 — SSE FastAPI endpoint

**Agent:** Multi-Agent Panel Specialist (L2)
**Read skill:** `thesis-card`, `streaming`

Create `src/apex/integrations/thesis_service.py`:
- FastAPI `APIRouter` with `GET /api/arb/{arb_id}/thesis`
- Reads `ArbOpportunity` from SQLite via `store.get_arb_opportunity(arb_id)`
- Streams Claude response as SSE (`text/event-stream`)
- Proper `Cache-Control: no-cache` and CORS headers

Register router in `autopilot-local/backend/main.py`:
```python
from thesis_service import router as thesis_router
app.include_router(thesis_router)
```

---

## Step 3 — ThesisCard frontend component

**Agent:** Frontend Engineer
**Read skill:** `thesis-card`, `streaming`

Create `autopilot-local/frontend/components/ThesisCard.tsx`:
- `"use client"` directive (mandatory — EventSource is browser-only)
- `EventSource` connection to `/api/arb/{arbId}/thesis`
- Progressive JSON parsing of streaming text
- Renders: settlement badge, divergence reason, bull/bear accordions, confidence, risk flags, one-liner

Props: `{ arbId: string; autoStart?: boolean }`

---

## Step 4 — Wire ThesisCard into Arb Radar

**Agent:** Frontend Engineer
**Read skill:** `frontend-arb`

Edit `autopilot-local/frontend/app/dashboard/arb-radar/page.tsx`:
- Import `ThesisCard`
- Add "AI Thesis" button to each row
- Toggle `ThesisCard` inline below the row when button clicked
- Pass `autoStart` prop so it begins streaming on reveal

---

## Step 5 — Test streaming end-to-end

Run backend:
```bash
cd autopilot-local/backend
uvicorn main:app --reload --port 8000
```

Test SSE endpoint:
```bash
curl -N http://localhost:8000/api/arb/TEST_ID/thesis
```

Expected output:
```
data: {"token": "{"}
data: {"token": "\n  \"settlement_verdict\":"}
...
data: [DONE]
```

If Anthropic API key is missing, the endpoint should return 500 with a clear error.

---

## Step 6 — Verification checklist

- [ ] `ThesisCard.tsx` has `"use client"` on line 1
- [ ] SSE response uses `media_type="text/event-stream"`
- [ ] EventSource `onerror` handler closes the stream
- [ ] `ArbThesis.one_liner` renders in the arb-radar table row
- [ ] JSON parse failures log a warning and return a default `ArbThesis` with `confidence="LOW"`
