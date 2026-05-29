# APEX Autopilot — Complete Pitch Speech & AI Build Brief

**Version:** 1.0  
**Date:** 2026-05-28  
**Purpose:** This document is the **single source of truth** for anyone (human or AI) building or delivering the APEX Autopilot investor pitch. It contains the full spoken narrative, expanded slide specifications, design system, demo script, diligence appendix, and explicit build instructions.

**Primary outputs an AI should produce from this brief:**
1. **PowerPoint** (`.pptx`) — 14–18 slides, 16:9, dark institutional theme  
2. **Speaker notes** embedded in each slide (copy from Section 4)  
3. **Optional:** One-page PDF leave-behind, 3-minute teaser script, appendix slides for technical diligence  

**Do not** use hide-on-load text animations that zero out opacity before JavaScript runs (users reported this looked like strikethrough). All body text must be **fully visible** on load.

---

## Table of Contents

1. [How to Use This Document (AI Builder Instructions)](#1-how-to-use-this-document-ai-builder-instructions)  
2. [Product Truth Sheet (Facts Only — Verify Before Pitch)](#2-product-truth-sheet-facts-only--verify-before-pitch)  
3. [Audience, Positioning, and Narrative Arc](#3-audience-positioning-and-narrative-arc)  
4. [Full Pitch Speech — Standard (12–15 minutes)](#4-full-pitch-speech--standard-1215-minutes)  
5. [Extended Pitch Speech — Deep Dive (25–30 minutes)](#5-extended-pitch-speech--deep-dive-2530-minutes)  
6. [Slide-by-Slide Build Specification](#6-slide-by-slide-build-specification)  
7. [Visual & Motion Design System](#7-visual--motion-design-system)  
8. [Live Demo Script (5–7 minutes)](#8-live-demo-script-57-minutes)  
9. [Objection Handling & FAQ](#9-objection-handling--faq)  
10. [Technical Diligence Appendix (for appendix slides or Q&A)](#10-technical-diligence-appendix-for-appendix-slides-or-qa)  
11. [Business, Market, and Go-to-Market Detail](#11-business-market-and-go-to-market-detail)  
12. [Roadmap & Execution Credibility](#12-roadmap--execution-credibility)  
13. [The Ask — Templates and Use of Funds](#13-the-ask--templates-and-use-of-funds)  
14. [Deliverable Checklist & Quality Gates](#14-deliverable-checklist--quality-gates)  

---

## 1. How to Use This Document (AI Builder Instructions)

### 1.1 Your job

You are building an **investor-grade pitch deck** for **APEX Autopilot**: an institutional-style, **paper-only** autonomous trading system for **prediction markets** (Kalshi + Polymarket), with a Bloomberg-style operator terminal, multi-agent intelligence, and deterministic risk gates.

### 1.2 Non-negotiables

| Rule | Detail |
|------|--------|
| Paper only | Never imply live capital deployment without explicit “future / gated” language. M01 paper checks are first in every execution path. |
| No black box | Emphasize **auditability**, **gate ordering**, **fail-fast risk**, and **operator controls**. |
| Accurate traction | Use live API verification (Section 2) before quoting opportunity/proposal counts. |
| No Anthropic in product story | LLMs route through `settings.get_llm_client()` — do not name vendor unless asked. |
| Architecture | Reference **L0–L4** pipeline consistently (ingestion → brain → agents → execution/risk → observability). |

### 1.3 Recommended deck structure

**Core deck:** 14 slides (expandable to 18 with appendix).  
**Aspect ratio:** 16:9 (13.333" × 7.5").  
**Tone:** Confident, technical-but-accessible, institutional (not crypto-hype, not retail-trader casual).

### 1.4 Files in repo for reference

| Asset | Path |
|-------|------|
| Architecture deep dive | `docs/architecture/master_plan_arch.md` |
| Execution control plane | `master_plan.md` |
| Daily runbooks | `one-year-daily/day-001.md` … `day-260.md` |
| Agent onboarding | `AGENTS.md` |
| Existing PPTX generator | `scripts/build_pitch_deck_pptx.py` |
| HTML deck (optional) | `presentation.html` |

### 1.5 Regeneration command (PPTX baseline)

```bash
python /home/aarav/Aarav/Autopilot/scripts/build_pitch_deck_pptx.py
# Output: /home/aarav/Aarav/Autopilot/APEX_Autopilot_Pitch_Deck.pptx
```

Enhance that script **or** build a new deck using Section 6 slide specs and Section 7 design tokens.

---

## 2. Product Truth Sheet (Facts Only — Verify Before Pitch)

Run these commands on the demo machine **the same day** as the pitch:

```bash
curl -s http://127.0.0.1:8000/health | head -c 500
curl -s http://127.0.0.1:8000/api/arb/opportunities | python3 -c "import sys,json; d=json.load(sys.stdin); print('arb_rows', len(d) if isinstance(d,list) else len(d.get('opportunities',d.get('data',[]))))"
curl -s http://127.0.0.1:8000/proposals | python3 -c "import sys,json; d=json.load(sys.stdin); print('proposals', len(d) if isinstance(d,list) else 'check shape')"
```

**Startup:** `bash /home/aarav/Aarav/Autopilot/start_all.sh` (uses Python with `uvicorn` installed).

### 2.1 What APEX Autopilot is (one paragraph)

APEX Autopilot is an **institutional-grade autonomous paper-trading engine** for **cross-platform prediction-market arbitrage**. It ingests Kalshi and Polymarket market data, scores opportunities through a finance “brain,” runs a **multi-agent panel** for thesis and verdicts, routes dual-leg paper execution through **fail-fast risk gates** (M01–M09 for arb), and streams full **L4 observability** to a Next.js terminal styled like a professional trading desk.

### 2.2 Layer map (L0–L4)

| Layer | Name | Responsibility | Key modules |
|-------|------|----------------|-------------|
| L0 | Ingestion | Market + external feeds, retries, health | `src/apex/layers/l0/ingestion.py` |
| L1 | Finance Brain | Scoring, spread, confidence, signals | `src/apex/layers/l1/brain.py` |
| L2 | Agent Panel | Multi-agent BUY/SKIP/WAIT, bounded budgets | `src/apex/layers/l2/agent_panel.py` |
| L3 | Execution + Risk | Dual-leg routing, M01-first gates | `src/apex/layers/l3/execution.py`, `risk_checks.py` |
| L4 | Observability | Audit logs, telemetry, operator stream | `src/apex/layers/l4/observability.py` |

### 2.3 Arb risk gate stack (M01–M09) — speak to these in diligence

| Gate | Purpose |
|------|---------|
| M00 | Valid opportunity (tickers / market IDs present) |
| M01 | **Paper only** — Alpaca paper + Polymarket paper flags required |
| M02 | Minimum net edge floor |
| M03 | 24h volume floors (Kalshi + Poly) |
| M04 | Price sanity (asks in valid range) |
| M05 | Settlement match score (blocks misaligned contracts) |
| M06 | Daily arb loss cap |
| M07 | Liquidity depth / VWAP slippage on both legs |
| M08 | Spread width on Kalshi orderbook |
| M09 | Fractional Kelly + CFTC notional cap |

Gates run **sequentially**; first failure **stops** execution with a logged rejection reason.

### 2.4 Traction snapshot (template — fill live)

| Capability | Status | Evidence endpoint / note |
|------------|--------|---------------------------|
| Arb opportunity generation | Live | `/api/arb/opportunities` (SQLite-backed store) |
| Proposals | Live | `/proposals` |
| Risk gates | Enforced | `RiskEngine.run_arb_paper()` — M01 first |
| Frontend terminal | Live | `autopilot-local/frontend` — Playwright E2E |
| Intelligence (Bright Data) | Active / tuning | Agent + cron verdict pipeline |
| Backtest / settlement | In roadmap / partial | `backtest_engine.py`, `settlement_auditor.py` |

**Note:** `/opportunities` (engine cache) may differ from `/api/arb/opportunities` — pitch the API the UI should bind to.

### 2.5 Program status (roadmap honesty)

- **10-week enterprise plan:** Weeks 1–3 complete (ingestion, L2 hive, cross-asset hooks); Week 4 (ML predictive arb) in production testing; Weeks 5–7 (DeFi treasury, VaR/Monte Carlo, execution state machine) underway.  
- **260-day daily runbooks:** All day files exist; days 001–020 enriched with concrete file/symbol targets (2026-05-28).  
- **Paper-only** is a **feature**, not a limitation — it enables fast iteration and audit-first culture.

---

## 3. Audience, Positioning, and Narrative Arc

### 3.1 Primary audiences

1. **Seed / Series A investors** — care about market size, wedge, team velocity, safety culture.  
2. **Strategic angels** (trading infra, fintech, data) — care about architecture moat and API surface.  
3. **Design partners** (small funds, prop desks, market makers) — care about pilot terms, controls, exportability.

### 3.2 Positioning statement

> **APEX Autopilot is the operating system for disciplined prediction-market execution** — combining cross-venue arbitrage radar, multi-agent intelligence, and institutional risk gates in a single auditable paper-trading stack.

### 3.3 What we are NOT

- Not a consumer “bot app” or Telegram signal group.  
- Not promising guaranteed returns.  
- Not live-money ready without explicit compliance and partner gates.  
- Not a general LLM wrapper — agents are **bounded**, logged, and subordinate to deterministic risk.

### 3.4 Narrative arc (emotional + logical)

1. **Hook** — Prediction markets went institutional; execution infrastructure did not.  
2. **Pain** — Speed, fragmentation, and risk discipline break manual workflows.  
3. **Insight** — Autonomy only works with **gates + observability**, not autonomy alone.  
4. **Product** — L0–L4 stack + terminal operators trust.  
5. **Proof** — Live paper system, APIs, tests, runbooks.  
6. **Moat** — Safety culture + data flywheel + cross-market matching.  
7. **Plan** — 260-day execution credibility.  
8. **Business** — Terminal → team → institutional.  
9. **Ask** — Capital, hires, pilots.  
10. **Close** — Category-defining OS for intelligent PM execution.

---

## 4. Full Pitch Speech — Standard (12–15 minutes)

*Delivery notes: ~140–160 words/minute. Pause after the hook and before the ask. Make eye contact on slides 1, 5, 9, and 14.*

---

### Slide 1 — Title (45–60 seconds)

Good [morning/afternoon]. I’m [Name] from **Team Autopilot**.

We’re building **APEX Autopilot** — an **institutional paper-trading platform** for **prediction markets**.

If you’ve watched Kalshi and Polymarket explode in liquidity, you’ve seen a new asset class emerge. What hasn’t emerged is the **infrastructure layer**: the equivalent of a Bloomberg terminal plus an execution and risk stack — built for **speed**, **cross-venue arbitrage**, and **auditability**.

APEX is that layer. We run a full **L0 through L4 pipeline** — ingestion, quantitative brain, multi-agent analysis, risk-checked execution, and operator-grade observability — entirely in **paper mode** today, so we can move fast without ever confusing experimentation with live capital.

On a typical run, we surface **on the order of a hundred** live arbitrage opportunities, generate **dozens of active proposals**, and enforce **paper-first risk gates** on every path before anything reaches execution.

We’re not asking you to bet on a slide deck. We’re asking you to bet on a **working system** with a **260-day execution runbook** behind it.

---

### Slide 2 — Problem (90 seconds)

Here’s the problem we see every day in prediction markets.

**First: fragmented data.** Kalshi order books, Polymarket CLOB prices, settlement language, macro feeds, news — they live in different silos. By the time a human reconciles “are these actually the same event?”, the edge is gone.

**Second: execution lag.** Real arb windows are often **seconds**, not minutes. Manual workflows — spreadsheets, ad-hoc scripts, Discord alerts — are structurally too slow.

**Third: inconsistent risk.** When teams bypass deterministic gates, you get policy drift: one trader sizes aggressively, another skips settlement checks, and post-trade forensics become arguments instead of logs.

The result isn’t just missed profit. It’s **alpha decay**, **avoidable blow-ups**, and **non-reproducible** decisions — the opposite of what institutional capital requires.

---

### Slide 3 — Market context (60 seconds) *[optional slide if deck has 14+ slides]*

Prediction markets are no longer a curiosity. They’re **event-driven derivatives** with exchange-grade volumes on regulated and on-chain venues.

The wedge we’re attacking first is **cross-venue structural arbitrage**: the same economic proposition priced differently on Kalshi versus Polymarket, after fees, settlement alignment, and executable depth.

That wedge is **high-frequency in time** but **low-frequency in count of competent operators** — because the hard part isn’t spotting a spread; it’s **proving** you can execute both legs safely.

---

### Slide 4 — Solution (2 minutes)

Our answer is not “another AI bot.” It’s a **controlled autonomous engine**.

**L0 — Ingestion.** We pull market and external intelligence with retries, health checks, and cache hydration. No silent stale data.

**L1 — Finance Brain.** We score opportunities: spreads, confidence calibration, signal composition. This is where quantitative discipline lives.

**L2 — Agent Panel.** Multiple agents produce thesis and verdicts — BUY, SKIP, WAIT — under **bounded budgets**. They inform; they do not override risk.

**L3 — Execution with risk.** Dual-leg paper routing through a **fail-fast gate stack**. **M01 paper-only runs first.** Every time.

**L4 — Observability.** Full telemetry: what we saw, what we scored, what we rejected, and why.

This architecture is the product. The terminal is the window; the pipeline is the moat.

---

### Slide 5 — Product / Terminal (90 seconds)

Operators interact through a **Bloomberg-style terminal** — dark, dense, serious.

Four surfaces matter:

1. **Arb Radar** — ranked opportunities with **net edge**, confidence, settlement alignment.  
2. **Autopilot Console** — live proposals, execution lifecycle, backend health.  
3. **Intelligence Layer** — external source checks, news risk, consensus overlays (e.g., Bright Data-backed flows).  
4. **Operator Controls** — paper enforcement, token-gated actions, deterministic fallbacks when LLM or external services fail.

We designed for **trust**: every consequential action should have a visible rationale and a log line an auditor can replay.

---

### Slide 6 — Traction (2 minutes)

Let me be specific about what exists **today**.

We run a **live FastAPI backend** with health checks and real arb generation. Hit `/api/arb/opportunities` and you get a **large, refreshed set** of ranked arbs — not a mock.

We generate **proposals** through the same stack operators see in the UI.

**Risk gates are not aspirational.** `M01_PAPER_REQUIRED` is the **first** check in the arb path. Then edge floors, volume, price sanity, settlement match, daily loss caps, liquidity / VWAP slippage, spread width, and Kelly/CFTC sizing — **sequential, fail-fast**.

The **Next.js frontend** is wired for dashboard flows; we use **Playwright** end-to-end tests to prevent regressions.

Intelligence pipelines are **integrated** with ongoing tuning — verdict flows, cron jobs, agent adapters — with **soft-fail** behavior so optional services never take down core trading.

We also maintain **103+ backend unit tests** in active development and a **260-day daily runbook** with concrete file targets — unusual for this stage, intentional for our stage.

*[If demo follows: “I’ll show you this live in under five minutes.”]*

---

### Slide 7 — Why we win / Moat (90 seconds)

Our moat compounds four ways:

**Safety-first by design.** Paper defaults and explicit gate ordering prevent the class of accidents that kill fintech companies in week one.

**Cross-market intelligence.** We combine microstructure with verified external signals in one structured context — not a chat thread.

**Operator trust.** Transparent logs and deterministic fallbacks mean the system is debuggable at 2 a.m.

**Data flywheel.** Every rejected trade is training data: calibration, settlement precision, model scoring — the roadmap’s Week 4+ ML and backtest loops.

Competitors can copy a dashboard. They cannot quickly copy **culture + architecture + runbooks**.

---

### Slide 8 — Roadmap (90 seconds)

We execute on a **260-day plan** — not vibes. Daily documents in `one-year-daily/` with verification commands.

**Phase 1 — Reliability:** unified startup, CI, regression prevention — what you’d demand before scaling capital.

**Phase 2 — Observability:** operator workflows, explainability, audit exports.

**Phase 3 — Signal quality:** settlement auditor precision, stricter calibration, stronger gates.

**Phases 4–5 — Scale & production readiness:** auth, deployment hardening, staged autonomy controls, multi-tenant fund features.

Parallel theme tracks: **WC2026 brain**, **cron architecture**, **scheduled agents**, **trading upgrades**, **historical calibration seed**.

The 10-week enterprise architecture doc describes the north star — ML imbalance, semantic matching, VaR, treasury — we ship incrementally with paper guardrails.

---

### Slide 9 — Business model (75 seconds)

Monetization follows trust:

**Tier 1 — Pro Terminal:** subscription for radar, intelligence overlays, simulation analytics.

**Tier 2 — Team Ops:** collaboration, policy controls, audit exports, strategy workspaces.

**Tier 3 — Institutional:** dedicated deployments, custom integrations, risk policy frameworks.

**Long-term:** performance-linked products **only after** live capital paths and compliance tracks exist.

We charge for **infrastructure and control**, not for “signals.”

---

### Slide 10 — Competition (60 seconds) *[optional slide]*

| Alternative | Weakness vs APEX |
|-------------|------------------|
| Manual + scripts | No unified risk, no audit stream |
| Generic LLM agents | No deterministic gates, no dual-leg execution |
| Single-venue tools | Miss cross-platform arb |
| Traditional EMS | Not built for PM settlement semantics |

We win where **execution + risk + PM-specific matching** meet.

---

### Slide 11 — Team (45 seconds) *[fill with real names/bios]*

Team Autopilot combines [markets / infra / ML / product] experience.

We’ve already shipped a multi-layer trading stack — not a Figma mock — and we document execution daily.

*[Insert founders, relevant exits, domain expertise in Kalshi/CFTC/regulatory context if applicable.]*

---

### Slide 12 — The Ask (90 seconds)

We’re raising **[$X]** on **[SAFE / priced round]** to fund **12 months** of build and go-to-market.

**Use of funds:**
- **40%** — reliability, compliance infrastructure, test and CI depth  
- **35%** — alpha refinement: settlement, ML scoring, execution state machine  
- **25%** — scalable hosted deployments and design-partner integrations  

**Hiring plan — 3 roles:** infrastructure/platform, quantitative modeling, product ops / operator UX.

**Partnership — 2 design partners:** institutions or sophisticated desks who will run paper pilots, stress our gates, and co-design export and policy features.

We want investors who understand that **autonomy without discipline is a liability** — and that prediction markets need an **operating system**, not another alert bot.

---

### Slide 13 — Closing (30 seconds)

Prediction markets are moving from niche to infrastructure. The winners will be teams that combine **speed**, **cross-venue intelligence**, and **institutional controls**.

**APEX Autopilot** is building that operating system — **autonomy with discipline**.

We’d welcome a **product demo**, **technical diligence**, and **pilot planning** conversations.

Thank you.

---

## 5. Extended Pitch Speech — Deep Dive (25–30 minutes)

Use this section for **partner meetings**, **technical diligence calls**, or **accelerator office hours**. It repeats Section 4 content with added depth; do not read verbatim in a 10-minute slot.

### 5.1 L0 ingestion — what to say (3 minutes)

- Kalshi and Polymarket have different **API shapes**, **fee models**, and **settlement rules**.  
- Ingestion normalizes to internal domain models (`src/apex/domain/models.py`).  
- `call_with_retries()` wraps external HTTP — transient failures don’t poison state.  
- Redis L2 orderbook cache optional path for M07 depth checks.  
- Health endpoints expose dependency status for operator terminal.

### 5.2 L1 brain — what to say (3 minutes)

- Gross spread ≠ net edge: fees, time decay, gas assumptions (see master_plan_arch formulas).  
- VWAP executable edge: reject if top-of-book depth cannot support **3× stake** (M07).  
- Confidence scores feed Kelly dampening (M09) with VIX-linked lambda.  
- Week 4 track: XGBoost imbalance / predictive spread collapse — **in production testing**.

### 5.3 L2 agents — what to say (3 minutes)

- Agent panel produces structured verdicts, not free-form trades.  
- Bounded token/time budgets per decision.  
- Consensus engine concept (roadmap): Risk Officer, Alpha Researcher, Execution Trader roles.  
- LLM client abstraction — swappable providers; **no hard dependency** on a single vendor.  
- Soft-fail: if Ollama/TradingAgents offline, system degrades gracefully (known gotcha in logs).

### 5.4 L3 execution — what to say (4 minutes)

Walk through **one arb** narratively:

1. Opportunity detected → stored in SQLite via `SQLiteStore` only.  
2. Operator or autopilot selects → proposal created.  
3. `run_arb_paper()` executes M01→M09; any fail → `rejection_reason` string logged.  
4. Dual-leg paper submission via integrations hub (Polymarket, Alpaca adapters).  
5. State machine (roadmap): LEG_1_PENDING → LEG_2_PENDING → FULLY_HEDGED / hedge triggers.

Emphasize: **fail-fast** is a feature for capital preservation.

### 5.5 L4 observability — what to say (2 minutes)

- Audit stream for operators (SSE via `autopilot-local/backend`).  
- Event taxonomy: detection, scoring, gate pass/fail, execution, settlement.  
- Future: Prometheus/Grafana, Slack pager (architecture doc).

### 5.6 Testing & engineering maturity (2 minutes)

```bash
python -m pytest tests/ -v
cd autopilot-local/frontend && npx playwright test
python scripts/verification/verify_roadmap_daily.py --start 1 --end 20
```

- Pre-commit / CI expectation: no merge without green tests on touched layers.  
- `start_all.sh` resolves Python with uvicorn — avoids silent backend failure.

### 5.7 Regulatory framing (2 minutes — careful, not legal advice)

- Kalshi: CFTC-regulated event contracts.  
- Polymarket: different jurisdictional profile; paper mode lets us explore matching without customer funds.  
- CFTC notional tracker (M09) shows we think about **position limits** early.  
- Live capital requires **compliance review**, **customer agreements**, and **venue-specific** approvals — explicitly gated.

---

## 6. Slide-by-Slide Build Specification

Build **14 core slides** (+ up to 4 appendix). For each slide: use **title**, **on-slide text** (minimal bullets), **speaker notes** (from Section 4), and **visual direction**.

### Slide 1 — Title

| Field | Content |
|-------|---------|
| Eyebrow | INSTITUTIONAL PAPER TRADING PLATFORM |
| Title | APEX Autopilot |
| Subtitle | Autonomous prediction-market intelligence and execution for Kalshi + Polymarket — with risk gates, operator controls, and full auditability. |
| KPIs | 100+ live arbs · L0–L4 architecture · 260-day runbook |
| Visual | Dark grid background, orange orb accents, accent bar left edge |

### Slide 2 — Problem

| Field | Content |
|-------|---------|
| Headline | Human traders miss speed, context, and discipline. |
| Columns | Fragmented Data · Execution Lag · Inconsistent Risk |
| Footer | Result: alpha decay, avoidable risk, poor reproducibility |

### Slide 3 — Market *(optional)*

| Field | Content |
|-------|---------|
| Headline | Cross-venue prediction markets need execution infrastructure. |
| Bullets | Kalshi + Polymarket liquidity growth · Structural arb wedge · Execution = moat |

### Slide 4 — Solution (L0–L4)

| Field | Content |
|-------|---------|
| Headline | A controlled autonomous engine — not a black box. |
| Timeline | L0 Ingestion → L1 Brain → L2 Agents → L3/L4 Risk + Observability |
| Diagram | Use mermaid or horizontal pipeline graphic |

### Slide 5 — Product

| Field | Content |
|-------|---------|
| Headline | Bloomberg-style terminal for autonomous decision support. |
| Grid | Arb Radar · Autopilot Console · Intelligence Layer · Operator Controls |

### Slide 6 — Traction

| Field | Content |
|-------|---------|
| Headline | Running today: real APIs, real gates, real terminal. |
| Table | Capability / Status / Signal / Evidence (see Section 2.4) |
| Callout | M01 runs first on every arb path |

### Slide 7 — Moat

| Field | Content |
|-------|---------|
| Headline | Compound moat: architecture + culture + data. |
| Grid | Safety-first · Cross-market intelligence · Operator trust · Data flywheel |

### Slide 8 — Roadmap

| Field | Content |
|-------|---------|
| Headline | 260 days: paper alpha → production-ready autonomy. |
| Phases | P1 Reliability · P2 Observability · P3 Signal · P4–5 Scale |
| Footer | Themes: WC2026, cron, scheduled agents, calibration |

### Slide 9 — Business model

| Field | Content |
|-------|---------|
| Headline | Terminal → Team → Institutional. |
| Tiers | Pro · Team Ops · Institutional · Performance (future) |

### Slide 10 — Competition *(optional)*

| Field | Content |
|-------|---------|
| Content | Comparison table (Section 4 slide 10) |

### Slide 11 — Team

| Field | Content |
|-------|---------|
| Content | Photos, names, 1-line credentials, advisors |

### Slide 12 — The Ask

| Field | Content |
|-------|---------|
| Headline | Partner to accelerate engine → platform. |
| KPIs | $X · 3 hires · 2 design partners |
| Body | Use of funds breakdown (Section 13) |

### Slide 13 — Closing

| Field | Content |
|-------|---------|
| Headline | Autonomy with discipline wins this market. |
| Subhead | Building the OS for intelligent prediction-market execution. |
| CTA | Demo · diligence · pilot planning |

### Slide 14 — Contact / QR

| Field | Content |
|-------|---------|
| Email, calendar link, GitHub/demo URL if public |

### Appendix A — Architecture diagram

Full L0–L4 mermaid from `master_plan_arch.md` (simplified for slide).

### Appendix B — Risk gate table

M01–M09 one-liners (Section 2.3).

### Appendix C — API surface

`/health`, `/api/arb/opportunities`, `/proposals`, SSE streams.

### Appendix D — Sample rejection log

Example `M05_SETTLEMENT_BLOCKED` or `M07_SLIPPAGE_EXCEEDED` string — shows transparency.

---

## 7. Visual & Motion Design System

### 7.1 Color tokens

| Token | Hex | Usage |
|-------|-----|-------|
| Background | `#0b0f17` | Slide background |
| Panel | `#101725` | Cards |
| Ink | `#f7f8fb` | Primary text |
| Muted | `#aab5ca` | Secondary text |
| Accent | `#ff6a1a` | Eyebrows, bars, highlights |
| Accent 2 | `#2d9dff` | Architecture labels |
| OK | `#2fe6a7` | “Live” status |
| Warn | `#ffcc54` | “Tuning” status |
| Danger | `#ff5b7a` | Failures (sparingly) |

### 7.2 Typography

- **Headlines:** Archivo 700–900 (or Calibri Bold if PPTX-safe)  
- **Body:** Space Grotesk 400–500 (or Calibri)  
- **Minimum body on slide:** 18pt projected; never below 14pt  

### 7.3 Layout rules

- Left accent bar: 0.12" orange vertical stripe on every slide.  
- Max 6 bullet lines per slide; max 12 words per bullet.  
- No paragraph blocks longer than 3 lines on-slide — detail goes to speaker notes.  
- Use tables for traction, not paragraphs.

### 7.4 Motion (HTML only)

- Allowed: subtle scroll-snap between slides, progress bar, keyboard nav.  
- **Forbidden:** `opacity: 0` on body text before interaction (caused strikethrough confusion).  
- Respect `prefers-reduced-motion`.

### 7.5 Imagery suggestions for AI designer

- Abstract orderbook heatmap (blurred, no real tickers).  
- Dual-exchange schematic (Kalshi ↔ Polymarket).  
- Terminal screenshot mock (blur sensitive IDs).  
- Pipeline diagram (L0–L4 icons).

---

## 8. Live Demo Script (5–7 minutes)

**Prereq:** `bash start_all.sh`; confirm `curl http://127.0.0.1:8000/health` returns APEX (not another service on :8000).

| Step | Action | Say this |
|------|--------|----------|
| 1 | Open frontend terminal | “This is the operator surface — radar, proposals, system status.” |
| 2 | Show arb list populated | “These are live ranked opportunities from our SQLite arb store — refreshed on a schedule.” |
| 3 | Click one opportunity | “You see net edge, confidence, settlement score — the brain already filtered noise.” |
| 4 | Show proposal flow | “A proposal is a candidate trade — still subject to gates.” |
| 5 | Trigger or show rejected trade log | “Here’s a rejection: M05 settlement blocked — fail-fast, logged, explainable.” |
| 6 | Show `/health` or settings | “Paper mode enforced at settings level — M01 double-checks at execution.” |
| 7 | Optional: intelligence panel | “External verdict pipeline enriches thesis — soft-fails if vendor offline.” |

**Fallback if UI empty:** Open API JSON for `/api/arb/opportunities` — narrate structure fields (`net_edge`, `settlement_match_score`, tickers).

---

## 9. Objection Handling & FAQ

| Objection | Response |
|-----------|----------|
| “Isn’t this just ChatGPT trading?” | Agents advise; **M01–M09 gates execute**. Every rejection is a string, not a vibe. |
| “Why paper only?” | **Velocity + safety.** We prove reproducibility before capital and compliance. |
| “Kalshi vs Poly legal risk?” | We paper-trade and match carefully; live requires legal review per venue. |
| “How big is TAM?” | Prediction market volume growth + structural arb + terminal SaaS — quantify with current venue volumes (update quarterly). |
| “Incumbent brokers?” | They’re not built for cross-venue PM settlement matching + agent audit streams. |
| “What if LLM is down?” | Deterministic fallbacks; optional intelligence degrades, core arb scan continues. |
| “Defensibility?” | Gate ordering culture, settlement graph, calibration flywheel, 260-day execution proof. |
| “Exit?” | Infrastructure acquisition by exchange/broker; or PM-native fund stack. |

---

## 10. Technical Diligence Appendix (for appendix slides or Q&A)

### 10.1 Core services map

| Service | Role |
|---------|------|
| `arb_engine.py` | Scan, rank, persist opportunities |
| `settlement_auditor.py` | Outcome resolution |
| `backtest_engine.py` | Historical performance |
| `engine.py` | Orchestration |
| `pm_trading.py` | PM paper logic |
| `sqlite_store.py` | All persistence |

### 10.2 Key domain types

Use typed `@dataclass` models — `ArbOpportunity`, `TradeProposal`, `ArbRiskCheckResult`, `RiskResult`.

### 10.3 Config

Single `BaseSettings` in `src/apex/core/config.py` — feature flags for paper, relax modes, demo mode.

### 10.4 Frontend

Next.js `autopilot-local/frontend/app/page.tsx` — terminal UX.

### 10.5 Tests

`python -m pytest tests/ -v` — target 80%+ on critical paths over time.

---

## 11. Business, Market, and Go-to-Market Detail

### 11.1 Ideal customer profile (ICP)

1. **Sophisticated retail syndicates** graduating from spreadsheets  
2. **Small prop / family office** exploring PM arb  
3. **Fintech teams** white-labeling radar + risk APIs  

### 11.2 Pilot offer (design partner)

- 90-day paper pilot  
- Weekly gate rejection review  
- Export: audit logs + policy config  
- Success metric: **time-to-decision** and **false positive rate** on executed paper arbs  

### 11.3 Pricing hypothesis

| Tier | Indicative | Includes |
|------|------------|----------|
| Pro | $500–2k/mo | Radar, basic intel, 1 seat |
| Team | $5–15k/mo | Policy, exports, 5–20 seats |
| Institutional | Custom | VPC, SSO, custom gates |

### 11.4 GTM sequence

1. Design partners (paper)  
2. Terminal SaaS  
3. API for quants  
4. Live capital (year 2+, compliance permitting)

---

## 12. Roadmap & Execution Credibility

### 12.1 Evidence we execute

- 260 daily markdown runbooks with verifier script  
- Days 001–020 regenerated with symbol-level tasks (2026-05-28)  
- Working local stack script fixed for Python/uvicorn discovery  

### 12.2 Near-term milestones (next 90 days)

| Week | Milestone |
|------|-----------|
| 1–2 | CI gates on startup + arb API regression tests |
| 3–4 | UI binds to canonical arb endpoint; opportunity count parity |
| 5–6 | Settlement auditor precision + rejection analytics dashboard |
| 7–8 | Design partner #1 onboarded |
| 9–12 | Auth + hosted staging environment |

### 12.3 Long-term (architecture north star)

From `master_plan_arch.md`: ML imbalance, semantic matcher v2, VaR Monte Carlo, DeFi treasury sweeper, multi-asset SOR — **staged behind paper gates**.

---

## 13. The Ask — Templates and Use of Funds

Replace `$X` with actual raise.

### 13.1 Raise scenarios (speaker optional detail)

| Scenario | Amount | Runway | Focus |
|----------|--------|--------|-------|
| Pre-seed | $750k–$1.5M | 12–15 mo | Reliability + 2 pilots |
| Seed | $2–4M | 18–24 mo | Team scale + hosted + ML |

### 13.2 Use of funds (default split)

- **40% Engineering reliability** — CI, observability, startup hardening, test coverage  
- **35% Quant + signal** — settlement, backtest, ML scoring, execution FSM  
- **25% GTM + pilots** — design partner success, terminal polish, docs  

### 13.3 Hiring profiles

1. **Platform/infra** — FastAPI, Redis, job scheduling, deployment  
2. **Quant** — market microstructure, calibration, risk metrics  
3. **Product ops** — operator UX, runbooks, partner onboarding  

---

## 14. Deliverable Checklist & Quality Gates

Before delivering any pitch asset, verify:

- [ ] All on-slide numbers match live `curl` checks (Section 2)  
- [ ] “Paper only” appears at least twice in deck  
- [ ] M01-first mentioned on traction or solution slide  
- [ ] No vendor lock-in claims without evidence  
- [ ] No `opacity: 0` text hiding in HTML  
- [ ] PPTX opens in PowerPoint without font fallback breaking layout  
- [ ] Speaker notes populated for every slide  
- [ ] Appendix includes risk gate table  
- [ ] Contact slide has real email/URL  
- [ ] Demo path rehearsed with `start_all.sh`  

### 14.1 AI builder prompt (copy-paste)

```
Read docs/pitch/APEX_Autopilot_Pitch_Brief_and_Speech.md in full.
Build a 16:9 .pptx with 14 slides + 2 appendix slides following Section 6 and Section 7 exactly.
Embed speaker notes from Section 4 for each slide.
Use python-pptx; extend scripts/build_pitch_deck_pptx.py.
Verify traction numbers against /api/arb/opportunities before finalizing slide 6.
Do not use strikethrough or hide text with opacity animations.
Output: APEX_Autopilot_Pitch_Deck_v2.pptx
```

---

## Document maintenance

| Change | Update |
|--------|--------|
| New risk gate | Section 2.3, 10, appendix B |
| New API endpoint | Section 2.4, 8, appendix C |
| Funding terms closed | Section 13 |
| Traction milestones | Section 2.4, slide 6 |

---

*End of pitch brief. This document is intended to be sufficient for a capable AI or human to produce a complete pitch deck, speech, and demo without additional context.*
