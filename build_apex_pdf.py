from __future__ import annotations

from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas

# ── Design tokens ──────────────────────────────────────────────────────────────
BG        = HexColor("#0b0f17")
PANEL     = HexColor("#101725")
INK       = HexColor("#f7f8fb")
MUTED     = HexColor("#aab5ca")
ACCENT    = HexColor("#ff6a1a")
ACCENT2   = HexColor("#2d9dff")
OK        = HexColor("#2fe6a7")
WARN      = HexColor("#ffcc54")
DANGER    = HexColor("#ff5b7a")
PANEL2    = HexColor("#151e2e")
BORDER    = HexColor("#1e2c42")

W, H = landscape(A4)   # 841.89 × 595.28 pt  ≈ 16:9-ish

# ── Helpers ────────────────────────────────────────────────────────────────────
def bg(c):
    c.setFillColor(BG)
    c.rect(0, 0, W, H, fill=1, stroke=0)

def accent_bar(c):
    c.setFillColor(ACCENT)
    c.rect(0, 0, 8, H, fill=1, stroke=0)

def eyebrow(c, text, x=30, y=None, color=ACCENT):
    if y is None:
        y = H - 44
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(color)
    c.drawString(x, y, text.upper())

def headline(c, text, x=30, y=None, size=32, color=INK):
    if y is None:
        y = H - 90
    c.setFont("Helvetica-Bold", size)
    c.setFillColor(color)
    c.drawString(x, y, text)

def subhead(c, text, x=30, y=None, size=14, color=MUTED):
    if y is None:
        y = H - 118
    c.setFont("Helvetica", size)
    c.setFillColor(color)
    c.drawString(x, y, text)

def body_text(c, text, x=30, y=None, size=11, color=INK):
    if y is None:
        y = H - 150
    c.setFont("Helvetica", size)
    c.setFillColor(color)
    c.drawString(x, y, text)

def pill(c, text, x, y, w=130, h=22, bg_color=PANEL2, text_color=ACCENT):
    c.setFillColor(bg_color)
    c.roundRect(x, y, w, h, 4, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(text_color)
    c.drawCentredString(x + w/2, y + 6, text)

def divider(c, x, y, w, color=BORDER):
    c.setStrokeColor(color)
    c.setLineWidth(0.5)
    c.line(x, y, x+w, y)

def kpi_box(c, label, value, x, y, w=160, h=60):
    c.setFillColor(PANEL2)
    c.roundRect(x, y, w, h, 6, fill=1, stroke=0)
    c.setStrokeColor(ACCENT)
    c.setLineWidth(1)
    c.roundRect(x, y, w, h, 6, fill=0, stroke=1)
    c.setFont("Helvetica-Bold", 20)
    c.setFillColor(ACCENT)
    c.drawCentredString(x + w/2, y + h - 26, value)
    c.setFont("Helvetica", 9)
    c.setFillColor(MUTED)
    c.drawCentredString(x + w/2, y + 10, label)

def card(c, title, lines, x, y, w=180, h=110, title_color=ACCENT2):
    c.setFillColor(PANEL2)
    c.roundRect(x, y, w, h, 6, fill=1, stroke=0)
    c.setStrokeColor(BORDER)
    c.setLineWidth(0.5)
    c.roundRect(x, y, w, h, 6, fill=0, stroke=1)
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(title_color)
    c.drawString(x+12, y+h-18, title)
    divider(c, x+8, y+h-25, w-16)
    c.setFont("Helvetica", 9)
    c.setFillColor(INK)
    ty = y + h - 40
    for line in lines:
        if ty < y + 10:
            break
        c.drawString(x+12, ty, line)
        ty -= 14

def slide_number(c, n, total=16):
    c.setFont("Helvetica", 8)
    c.setFillColor(MUTED)
    c.drawRightString(W - 14, 12, f"{n} / {total}")

def wrap_text(c, text, x, y, max_width, font="Helvetica", size=11, color=INK, line_height=16):
    """Simple word-wrap helper."""
    c.setFont(font, size)
    c.setFillColor(color)
    words = text.split()
    line = ""
    cur_y = y
    for word in words:
        test = (line + " " + word).strip()
        if c.stringWidth(test, font, size) <= max_width:
            line = test
        else:
            c.drawString(x, cur_y, line)
            cur_y -= line_height
            line = word
    if line:
        c.drawString(x, cur_y, line)
    return cur_y - line_height

# ══════════════════════════════════════════════════════════════════════════════
# SLIDE BUILDERS
# ══════════════════════════════════════════════════════════════════════════════

def slide_title(c):
    bg(c); accent_bar(c)
    # Glowing orb decoration
    c.setFillColor(HexColor("#ff6a1a22"))
    c.circle(W - 120, H - 80, 120, fill=1, stroke=0)
    c.setFillColor(HexColor("#2d9dff11"))
    c.circle(W - 60, 60, 80, fill=1, stroke=0)

    eyebrow(c, "INSTITUTIONAL PAPER TRADING PLATFORM", x=30, y=H-50)
    c.setFont("Helvetica-Bold", 52)
    c.setFillColor(INK)
    c.drawString(30, H-130, "APEX Autopilot")
    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(ACCENT)
    c.drawString(30, H-152, "Autonomous Prediction-Market Execution Engine")

    c.setFont("Helvetica", 11)
    c.setFillColor(MUTED)
    desc = "AI-governed cross-venue arbitrage for Kalshi × Polymarket — with a 14-check"
    desc2 = "risk stack, multi-agent intelligence, and Bloomberg-style operator terminal."
    c.drawString(30, H-178, desc)
    c.drawString(30, H-194, desc2)

    divider(c, 30, H-210, W-60)

    # KPI pills
    kw = 180
    kh = 55
    ky = H-290
    kpi_box(c, "Live Arb Opportunities", "100+",     30,          ky, kw, kh)
    kpi_box(c, "Architecture Layers",   "L0–L4",    30+kw+12,    ky, kw, kh)
    kpi_box(c, "Daily Execution Plan",  "260 Days", 30+2*(kw+12),ky, kw, kh)
    kpi_box(c, "Risk Gates",            "M01–M09",  30+3*(kw+12),ky, kw, kh)

    # Repo badge
    c.setFont("Helvetica", 9)
    c.setFillColor(MUTED)
    c.drawString(30, 30, "github.com/aaravjj2/Autopilot-public  ·  Apache-2.0  ·  Paper-only v1.0")
    slide_number(c, 1)

def slide_problem(c):
    bg(c); accent_bar(c)
    eyebrow(c, "The Problem")
    headline(c, "Human traders miss speed, context, and discipline.", size=24, y=H-88)

    cols = [
        ("📡  Fragmented Data", [
            "Kalshi order books, Polymarket CLOB,",
            "settlement language, macro feeds —",
            "each in a different silo.",
            "Edge is gone by reconciliation time.",
        ]),
        ("⚡  Execution Lag", [
            "Real arb windows: seconds, not minutes.",
            "Spreadsheets and Discord alerts are",
            "structurally too slow to capture",
            "cross-venue structural spreads.",
        ]),
        ("🎲  Inconsistent Risk", [
            "No deterministic gates → policy drift.",
            "One trader sizes aggressively,",
            "another skips settlement checks.",
            "Post-trade forensics become arguments.",
        ]),
    ]
    cw = (W - 80) / 3
    cy = H - 340
    for i, (title, lines) in enumerate(cols):
        cx = 30 + i * (cw + 10)
        card(c, title, lines, cx, cy, w=cw-5, h=160, title_color=WARN)

    divider(c, 30, cy - 18, W - 60)
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(DANGER)
    result = "Result: alpha decay  ·  avoidable blow-ups  ·  non-reproducible decisions"
    c.drawCentredString(W/2, cy - 32, result)
    slide_number(c, 2)

def slide_market(c):
    bg(c); accent_bar(c)
    eyebrow(c, "Market Context")
    headline(c, "Cross-venue prediction markets need execution infrastructure.", size=22, y=H-88)

    pts = [
        ("Regulated & on-chain venues", "Kalshi (CFTC-regulated) and Polymarket both reached exchange-grade volumes. Event-driven derivatives are no longer a curiosity — they're an asset class."),
        ("The structural arb wedge",    "The same economic proposition priced differently across venues, after fees, settlement alignment, and executable depth. High-frequency in time; low in competent operators."),
        ("Execution = the moat",        "Spotting a spread is commoditised. Proving you can execute both legs safely, with an audit trail, is not. That's the wedge we're attacking."),
        ("260-day runway ahead",        "APEX compounds a data flywheel from every rejected trade: calibration, settlement precision, model scoring — structural advantages that grow over time."),
    ]
    y = H - 145
    for title, body in pts:
        c.setFillColor(PANEL2)
        c.roundRect(30, y - 36, W - 60, 46, 5, fill=1, stroke=0)
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(ACCENT2)
        c.drawString(44, y + 2, title)
        c.setFont("Helvetica", 10)
        c.setFillColor(INK)
        c.drawString(44, y - 16, body[:100])
        if len(body) > 100:
            c.drawString(44, y - 28, body[100:].strip())
        y -= 58

    slide_number(c, 3)

def slide_solution(c):
    bg(c); accent_bar(c)
    eyebrow(c, "Solution — L0–L4 Architecture")
    headline(c, "A controlled autonomous engine — not a black box.", size=24, y=H-88)

    layers = [
        ("L0", "Ingestion",        ACCENT2,  "Market + external feeds, retries,\ncache hydration, health checks."),
        ("L1", "Finance Brain",    OK,       "Gross→net spread, confidence\ncalibration, signal composition."),
        ("L2", "Agent Panel",      WARN,     "Multi-agent BUY/SKIP/WAIT under\nbounded budgets. Inform, not override."),
        ("L3", "Execution + Risk", ACCENT,   "Dual-leg paper routing through\nM01–M09 fail-fast gate stack."),
        ("L4", "Observability",    MUTED,    "Full telemetry: what we saw, scored,\nrejected, and why. Auditor-grade logs."),
    ]

    bw = (W - 80) / 5
    by = H - 160
    prev_cx = None
    for i, (lbl, name, col, desc) in enumerate(layers):
        bx = 30 + i * (bw + 8)
        h_box = 220
        c.setFillColor(PANEL2)
        c.roundRect(bx, by - h_box, bw, h_box, 6, fill=1, stroke=0)
        c.setStrokeColor(col)
        c.setLineWidth(1.5)
        c.roundRect(bx, by - h_box, bw, h_box, 6, fill=0, stroke=1)
        # Layer badge
        c.setFillColor(col)
        c.roundRect(bx + 8, by - 24, 28, 20, 4, fill=1, stroke=0)
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(BG)
        c.drawCentredString(bx + 22, by - 18, lbl)
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(INK)
        c.drawString(bx + 10, by - 44, name)
        divider(c, bx+6, by - 52, bw - 12, col)
        c.setFont("Helvetica", 9)
        c.setFillColor(MUTED)
        ty = by - 68
        for line in desc.split("\n"):
            c.drawString(bx + 10, ty, line)
            ty -= 14
        # Arrow between boxes
        if prev_cx is not None:
            c.setStrokeColor(MUTED)
            c.setLineWidth(0.8)
            mid_y = by - h_box/2
            c.line(prev_cx + bw + 2, mid_y, bx - 2, mid_y)
            c.setFillColor(MUTED)
            c.drawString(bx - 7, mid_y - 3, "▶")
        prev_cx = bx

    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(MUTED)
    c.drawCentredString(W/2, 28, "Architecture is the moat. The terminal is the window.")
    slide_number(c, 4)

def slide_product(c):
    bg(c); accent_bar(c)
    eyebrow(c, "Product — Operator Terminal")
    headline(c, "Bloomberg-style terminal for autonomous decision support.", size=22, y=H-88)

    surfaces = [
        ("📊  Arb Radar",
         ["Ranked opportunities with net edge,", "confidence score, settlement alignment.", "Refreshed from live SQLite arb store.", "Colour-coded priority tiers."],
         ACCENT),
        ("🤖  Autopilot Console",
         ["Live proposals, execution lifecycle,", "backend health indicators.", "Real-time gate pass/fail visibility.", "Paper-enforcement status badge."],
         ACCENT2),
        ("🧠  Intelligence Layer",
         ["External source checks, news risk,", "consensus overlays (Bright Data-backed).", "Soft-fail: optional services never", "take down core trading flow."],
         OK),
        ("🔐  Operator Controls",
         ["Paper enforcement toggle.", "Token-gated high-impact actions.", "Deterministic fallbacks on LLM/API fail.", "Full audit stream replay."],
         WARN),
    ]
    cw = (W - 80) / 2 - 5
    ch = 150
    positions = [(30, H-310), (30+cw+10, H-310), (30, H-470), (30+cw+10, H-470)]
    for (title, lines, col), (px, py) in zip(surfaces, positions):
        card(c, title, lines, px, py, w=cw, h=ch, title_color=col)

    slide_number(c, 5)

def slide_traction(c):
    bg(c); accent_bar(c)
    eyebrow(c, "Traction — What Exists Today")
    headline(c, "Running today: real APIs, real gates, real terminal.", size=24, y=H-88)

    rows = [
        ["Capability", "Status", "Evidence"],
        ["Arb opportunity generation",  "✅ LIVE",     "/api/arb/opportunities — SQLite-backed, refreshed"],
        ["Active proposals",            "✅ LIVE",     "/proposals — wired to operator terminal"],
        ["M01–M09 risk gates",          "✅ ENFORCED", "RiskEngine.run_arb_paper() — M01-first, fail-fast"],
        ["Next.js operator terminal",   "✅ LIVE",     "autopilot-local/frontend + Playwright E2E"],
        ["Intelligence pipeline",       "🔶 TUNING",   "Agent verdict flows, cron jobs, Bright Data adapter"],
        ["103+ unit tests",             "✅ ACTIVE",   "pytest tests/ — critical path coverage"],
        ["Backtest / settlement",        "📍 ROADMAP",  "backtest_engine.py, settlement_auditor.py"],
    ]

    col_w = [200, 100, W - 80 - 310]
    row_h = 28
    tx = 30
    ty = H - 130

    for ri, row in enumerate(rows):
        rx = tx
        is_header = ri == 0
        for ci, (cell, cw) in enumerate(zip(row, col_w)):
            bg_c = PANEL if ri % 2 == 0 and not is_header else (PANEL2 if not is_header else HexColor("#1a2540"))
            c.setFillColor(bg_c)
            c.rect(rx, ty - row_h, cw, row_h, fill=1, stroke=0)
            if is_header:
                c.setFont("Helvetica-Bold", 9)
                c.setFillColor(ACCENT)
            else:
                c.setFont("Helvetica", 9)
                if "✅" in cell:
                    c.setFillColor(OK)
                elif "🔶" in cell:
                    c.setFillColor(WARN)
                elif "📍" in cell:
                    c.setFillColor(MUTED)
                else:
                    c.setFillColor(INK)
            c.drawString(rx + 8, ty - row_h + 9, cell)
            rx += cw
        ty -= row_h

    # Callout
    c.setFillColor(HexColor("#ff6a1a22"))
    c.roundRect(30, ty - 34, W - 60, 28, 5, fill=1, stroke=0)
    c.setStrokeColor(ACCENT)
    c.setLineWidth(0.8)
    c.roundRect(30, ty - 34, W - 60, 28, 5, fill=0, stroke=1)
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(ACCENT)
    c.drawCentredString(W/2, ty - 22, "M01 PAPER_REQUIRED runs first on every single arb execution path — without exception.")

    slide_number(c, 6)

def slide_moat(c):
    bg(c); accent_bar(c)
    eyebrow(c, "Competitive Moat")
    headline(c, "Compound moat: architecture + culture + data flywheel.", size=22, y=H-88)

    moats = [
        ("🔒  Safety-First by Design",
         "Paper defaults and deterministic gate ordering prevent the class of accidents that kill fintech companies early. M01 is not a checkbox — it is the contract.",
         ACCENT),
        ("🌐  Cross-Market Intelligence",
         "We combine microstructure signals with verified external data in one structured context. Not a chat thread. Not a prompt — a typed decision pipeline with rollback.",
         ACCENT2),
        ("🔍  Operator Trust",
         "Transparent logs and deterministic fallbacks mean the system is debuggable at 2 a.m. Operators see every gate decision, every rejection reason, every verdict.",
         OK),
        ("📈  Data Flywheel",
         "Every rejected trade is training data: calibration, settlement precision, model scoring. Week 4+ ML loops compound this advantage against anyone starting today.",
         WARN),
    ]

    for i, (title, body, col) in enumerate(moats):
        mx = 30 if i % 2 == 0 else W/2 + 5
        my = H - 200 if i < 2 else H - 360
        mw = W/2 - 40
        mh = 110

        c.setFillColor(PANEL2)
        c.roundRect(mx, my, mw, mh, 6, fill=1, stroke=0)
        c.setStrokeColor(col)
        c.setLineWidth(1)
        c.roundRect(mx, my, mw, mh, 6, fill=0, stroke=1)
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(col)
        c.drawString(mx + 12, my + mh - 20, title)
        divider(c, mx + 8, my + mh - 28, mw - 16, col)

        c.setFont("Helvetica", 9)
        c.setFillColor(INK)
        words = body.split()
        line = ""
        ty2 = my + mh - 44
        for word in words:
            test = (line + " " + word).strip()
            if c.stringWidth(test, "Helvetica", 9) <= mw - 24:
                line = test
            else:
                c.drawString(mx + 12, ty2, line)
                ty2 -= 13
                line = word
                if ty2 < my + 8:
                    break
        if line and ty2 >= my + 8:
            c.drawString(mx + 12, ty2, line)

    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(MUTED)
    c.drawCentredString(W/2, 28, "Competitors can copy a dashboard. They cannot quickly copy culture + architecture + runbooks.")
    slide_number(c, 7)

def slide_roadmap(c):
    bg(c); accent_bar(c)
    eyebrow(c, "Roadmap — 260-Day Execution Plan")
    headline(c, "260 days: paper alpha  →  production-ready autonomy.", size=24, y=H-88)

    phases = [
        ("P1\nReliability",  "Wks 1–4",  "Unified startup, CI gates, regression prevention, arb API parity.", ACCENT),
        ("P2\nObservability","Wks 5–8",  "Operator workflows, explainability, audit log exports, terminal polish.", ACCENT2),
        ("P3\nSignal Quality","Wks 9–12", "Settlement auditor precision, stricter calibration, stronger gate logic.", OK),
        ("P4\nScale",         "Wks 13–20","Auth, hosted staging, staged autonomy controls, multi-tenant fund features.", WARN),
        ("P5\nProduction",    "Wks 21–36","Live capital path compliance review, VaR/Monte Carlo, execution state machine.", MUTED),
    ]

    pw = (W - 80) / 5
    py_base = H - 160
    bar_h = 200
    for i, (name, timing, desc, col) in enumerate(phases):
        px = 30 + i * (pw + 8)
        fill_h = bar_h * (0.3 + i * 0.1)  # visual progress feel
        c.setFillColor(PANEL2)
        c.roundRect(px, py_base - bar_h, pw, bar_h, 5, fill=1, stroke=0)
        c.setFillColor(HexColor(col.hexval().replace("#","") + "33" if hasattr(col, 'hexval') else "#ffffff22"))
        # Just use a subtle tint instead
        c.setFillColor(PANEL)
        c.roundRect(px, py_base - fill_h, pw, fill_h, 5, fill=1, stroke=0)
        c.setStrokeColor(col)
        c.setLineWidth(1.2)
        c.roundRect(px, py_base - bar_h, pw, bar_h, 5, fill=0, stroke=1)
        # phase label
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(col)
        for j, ln in enumerate(name.split("\n")):
            c.drawCentredString(px + pw/2, py_base - 20 - j*14, ln)
        c.setFont("Helvetica", 8)
        c.setFillColor(MUTED)
        c.drawCentredString(px + pw/2, py_base - bar_h + 48, timing)
        # desc
        words = desc.split()
        line = ""
        ty = py_base - bar_h + 38
        c.setFont("Helvetica", 7.5)
        c.setFillColor(INK)
        for word in words:
            test = (line + " " + word).strip()
            if c.stringWidth(test, "Helvetica", 7.5) <= pw - 14:
                line = test
            else:
                c.drawString(px + 7, ty, line)
                ty -= 11
                line = word
        if line:
            c.drawString(px + 7, ty, line)

    # parallel themes
    themes = ["WC2026 Brain", "Cron Architecture", "Scheduled Agents", "Historical Calibration", "Trading Upgrades"]
    tx = 30
    ty = py_base - bar_h - 28
    for t in themes:
        pill(c, t, tx, ty, w=130, h=20, bg_color=HexColor("#1a2540"), text_color=ACCENT2)
        tx += 138

    slide_number(c, 8)

def slide_business(c):
    bg(c); accent_bar(c)
    eyebrow(c, "Business Model")
    headline(c, "Terminal  →  Team  →  Institutional.", size=28, y=H-88)
    subhead(c, "Monetisation follows operator trust. We charge for infrastructure and control — not signals.", y=H-116)

    tiers = [
        ("Pro Terminal",   "$500–$2k/mo",  ACCENT,  ["Arb radar", "Intelligence overlays", "Simulation analytics", "1 seat"]),
        ("Team Ops",       "$5–$15k/mo",   ACCENT2, ["Policy controls", "Audit log exports", "Strategy workspaces", "5–20 seats"]),
        ("Institutional",  "Custom",       OK,      ["Dedicated VPC deploy", "SSO + custom gates", "Risk policy frameworks", "SLA + white-glove"]),
        ("Performance\n(Future)",  "Rev-share",    WARN,    ["Live capital paths only", "Compliance-gated", "After Year 2+", "Venue approval req'd"]),
    ]

    tw = (W - 80) / 4 - 8
    th = 190
    ty = H - 160
    for i, (name, price, col, items) in enumerate(tiers):
        tx = 30 + i * (tw + 10)
        c.setFillColor(PANEL2)
        c.roundRect(tx, ty - th, tw, th, 6, fill=1, stroke=0)
        c.setStrokeColor(col)
        c.setLineWidth(1.5)
        c.roundRect(tx, ty - th, tw, th, 6, fill=0, stroke=1)
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(col)
        for j, ln in enumerate(name.split("\n")):
            c.drawCentredString(tx + tw/2, ty - 18 - j*14, ln)
        c.setFont("Helvetica-Bold", 14)
        c.setFillColor(INK)
        c.drawCentredString(tx + tw/2, ty - 50, price)
        divider(c, tx + 8, ty - 60, tw - 16, col)
        c.setFont("Helvetica", 9)
        iy = ty - 76
        for item in items:
            c.setFillColor(col)
            c.drawString(tx + 12, iy, "›")
            c.setFillColor(MUTED)
            c.drawString(tx + 22, iy, item)
            iy -= 16

    slide_number(c, 9)

def slide_competition(c):
    bg(c); accent_bar(c)
    eyebrow(c, "Competition")
    headline(c, "APEX wins where execution + risk + PM-specific matching meet.", size=21, y=H-88)

    rows = [
        ["Alternative",           "Their Gap",                            "APEX Advantage"],
        ["Manual + scripts",      "No unified risk; no audit stream",     "Full M01–M09 gate stack + SSE logs"],
        ["Generic LLM agents",    "No deterministic gates; no dual-leg",  "Agents inform; gates decide"],
        ["Single-venue tools",    "Miss cross-platform arb",              "Kalshi × Polymarket dual-leg routing"],
        ["Traditional EMS",       "Not built for PM settlement semantics","Typed settlement-match scoring (M05)"],
        ["Ad-hoc quant scripts",  "No operator UX; no observability",     "Bloomberg-style terminal + L4 telemetry"],
    ]

    col_w = [180, 260, W - 80 - 450]
    row_h = 32
    tx = 30
    ty = H - 130

    for ri, row in enumerate(rows):
        rx = tx
        is_header = ri == 0
        for ci, (cell, cw) in enumerate(zip(row, col_w)):
            bg_c = (HexColor("#1a2540") if is_header else (PANEL2 if ri % 2 == 0 else PANEL))
            c.setFillColor(bg_c)
            c.rect(rx, ty - row_h, cw, row_h, fill=1, stroke=0)
            if is_header:
                c.setFont("Helvetica-Bold", 9)
                c.setFillColor(ACCENT)
            elif ci == 2:
                c.setFont("Helvetica-Bold", 9)
                c.setFillColor(OK)
            elif ci == 1:
                c.setFont("Helvetica", 9)
                c.setFillColor(DANGER)
            else:
                c.setFont("Helvetica", 9)
                c.setFillColor(INK)
            c.drawString(rx + 8, ty - row_h + 11, cell)
            rx += cw
        ty -= row_h

    slide_number(c, 10)

def slide_team(c):
    bg(c); accent_bar(c)
    eyebrow(c, "Team")
    headline(c, "Built by practitioners — shipped daily, not Figma-first.", size=24, y=H-88)

    c.setFont("Helvetica", 11)
    c.setFillColor(MUTED)
    c.drawString(30, H-116, "Team Autopilot — markets × infra × ML × product.")

    # Placeholder team cards
    roles = [
        ("Aarav J.", "Founder & Lead Engineer", "Full L0–L4 stack architect.\n260-day daily runbook author.\nKalshi + Polymarket API integrations.", ACCENT),
        ("[ Quant ]", "Quantitative Modeler", "Market microstructure.\nCalibration, risk metrics, Kelly/VaR.\nML scoring pipeline (Week 4+ track).", ACCENT2),
        ("[ Infra ]", "Platform Engineer", "FastAPI, Redis, job scheduling.\nDocker/CI deployment hardening.\nObservability + test coverage.", OK),
        ("[ Product ]","Product & Ops", "Operator UX, runbooks.\nDesign partner onboarding.\nPM settlement graph research.", WARN),
    ]

    rw = (W - 80) / 4 - 8
    rh = 200
    ry = H - 160
    for i, (name, role, bio, col) in enumerate(roles):
        rx = 30 + i * (rw + 10)
        # Avatar circle
        c.setFillColor(PANEL2)
        c.roundRect(rx, ry - rh, rw, rh, 6, fill=1, stroke=0)
        c.setStrokeColor(col)
        c.setLineWidth(1)
        c.roundRect(rx, ry - rh, rw, rh, 6, fill=0, stroke=1)
        c.setFillColor(HexColor("#1e2c42"))
        c.circle(rx + rw/2, ry - 32, 22, fill=1, stroke=0)
        c.setFont("Helvetica-Bold", 16)
        c.setFillColor(col)
        c.drawCentredString(rx + rw/2, ry - 38, name[0])
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(INK)
        c.drawCentredString(rx + rw/2, ry - 66, name)
        c.setFont("Helvetica", 8)
        c.setFillColor(col)
        c.drawCentredString(rx + rw/2, ry - 80, role)
        divider(c, rx + 8, ry - 90, rw - 16, col)
        c.setFont("Helvetica", 8)
        c.setFillColor(MUTED)
        ty2 = ry - 104
        for ln in bio.split("\n"):
            c.drawCentredString(rx + rw/2, ty2, ln)
            ty2 -= 13

    slide_number(c, 11)

def slide_ask(c):
    bg(c); accent_bar(c)
    eyebrow(c, "The Ask")
    headline(c, "Partner to accelerate engine  →  platform.", size=26, y=H-88)

    # KPIs
    kw, kh = 155, 55
    kpi_box(c, "Raise (SAFE / Priced)",  "$[X]",    30,              H-165, kw, kh)
    kpi_box(c, "Runway",                "12–18 mo", 30+kw+10,        H-165, kw, kh)
    kpi_box(c, "Engineering Hires",     "3 Roles",  30+2*(kw+10),    H-165, kw, kh)
    kpi_box(c, "Design Partners",       "2 Pilots", 30+3*(kw+10),    H-165, kw, kh)

    divider(c, 30, H-228, W - 60)

    # Use of funds
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(ACCENT)
    c.drawString(30, H-248, "USE OF FUNDS")

    fund_items = [
        ("40%", "Engineering Reliability",  "CI, observability, startup hardening, test coverage depth", ACCENT),
        ("35%", "Quant + Signal Quality",   "Settlement, backtest, ML scoring, execution state machine", ACCENT2),
        ("25%", "GTM + Design Partners",    "Terminal polish, pilot onboarding, docs, partner success",  OK),
    ]
    fy = H - 265
    for pct, title, desc, col in fund_items:
        c.setFillColor(PANEL2)
        c.roundRect(30, fy - 30, W - 60, 34, 4, fill=1, stroke=0)
        c.setFillColor(col)
        c.rect(30, fy - 30, 42, 34, fill=1, stroke=0)
        c.setFont("Helvetica-Bold", 12)
        c.setFillColor(BG)
        c.drawCentredString(51, fy - 10, pct)
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(INK)
        c.drawString(82, fy - 6, title)
        c.setFont("Helvetica", 9)
        c.setFillColor(MUTED)
        c.drawString(82, fy - 20, desc)
        fy -= 40

    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(ACCENT)
    c.drawString(30, fy - 8, "HIRING PLAN")
    hires = ["Platform/Infra — FastAPI, Redis, deployment", "Quant — microstructure, calibration, risk metrics", "Product Ops — operator UX, partner onboarding"]
    hx = 30
    for hire in hires:
        pill(c, hire, hx, fy - 32, w=230, h=22, bg_color=PANEL2, text_color=MUTED)
        hx += 238

    slide_number(c, 12)

def slide_closing(c):
    bg(c); accent_bar(c)
    # Orb decoration
    c.setFillColor(HexColor("#ff6a1a1a"))
    c.circle(W/2, H/2, 200, fill=1, stroke=0)
    c.setFillColor(HexColor("#2d9dff0d"))
    c.circle(W/2, H/2, 280, fill=1, stroke=0)

    c.setFont("Helvetica-Bold", 36)
    c.setFillColor(INK)
    c.drawCentredString(W/2, H/2 + 60, "Autonomy with discipline")
    c.setFont("Helvetica-Bold", 20)
    c.setFillColor(ACCENT)
    c.drawCentredString(W/2, H/2 + 24, "wins this market.")

    divider(c, W/2 - 150, H/2 + 8, 300)

    c.setFont("Helvetica", 12)
    c.setFillColor(MUTED)
    c.drawCentredString(W/2, H/2 - 16, "Building the operating system for intelligent prediction-market execution.")

    for i, cta in enumerate(["Product Demo", "Technical Diligence", "Pilot Planning"]):
        pill(c, cta, W/2 - 210 + i*148, H/2 - 60, w=136, h=28, bg_color=PANEL2, text_color=ACCENT)

    slide_number(c, 13)

def slide_contact(c):
    bg(c); accent_bar(c)
    eyebrow(c, "Contact & Links")
    headline(c, "APEX Autopilot", size=28, y=H-90)

    c.setFont("Helvetica", 12)
    c.setFillColor(MUTED)
    c.drawString(30, H-120, "Team Autopilot  ·  Prediction-Market Execution Infrastructure")

    divider(c, 30, H-138, W-60)

    links = [
        ("🔗  GitHub",    "github.com/aaravjj2/Autopilot-public"),
        ("📄  License",   "Apache 2.0 — open source"),
        ("💻  Demo Mode", "export DEMO_MODE=true && python scripts/seed_demo.py"),
        ("🚀  Start All", "bash start_all.sh  →  http://localhost:8000/health"),
        ("📬  Email",     "[your-email@domain.com]"),
    ]
    ly = H - 165
    for icon_label, val in links:
        c.setFillColor(PANEL2)
        c.roundRect(30, ly - 22, W - 60, 26, 4, fill=1, stroke=0)
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(ACCENT2)
        c.drawString(44, ly - 10, icon_label)
        c.setFont("Helvetica", 10)
        c.setFillColor(INK)
        c.drawString(200, ly - 10, val)
        ly -= 32

    # Paper-only badge
    c.setFillColor(HexColor("#2fe6a722"))
    c.roundRect(30, 30, 250, 30, 5, fill=1, stroke=0)
    c.setStrokeColor(OK)
    c.setLineWidth(0.8)
    c.roundRect(30, 30, 250, 30, 5, fill=0, stroke=1)
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(OK)
    c.drawCentredString(155, 48, "✓  PAPER-ONLY MODE ENFORCED  (M01-FIRST)")
    slide_number(c, 14)

# ── Appendix slides ────────────────────────────────────────────────────────────

def slide_appendix_gates(c):
    bg(c); accent_bar(c)
    eyebrow(c, "Appendix B — Risk Gate Stack", color=MUTED)
    headline(c, "M01–M09: Sequential, Fail-Fast, Logged.", size=22, y=H-88)

    gates = [
        ("M00", "Valid Opportunity",    "Tickers / market IDs present and parseable",                     MUTED),
        ("M01", "PAPER ONLY ★",         "Alpaca paper + Polymarket paper flags required — runs FIRST",    DANGER),
        ("M02", "Net Edge Floor",        "Minimum net spread after fees must exceed threshold",             ACCENT),
        ("M03", "24h Volume Floors",     "Both Kalshi and Polymarket legs must meet volume minimums",       ACCENT2),
        ("M04", "Price Sanity",          "Asks must be in valid probability range [0.01, 0.99]",            OK),
        ("M05", "Settlement Match",      "Blocks contracts with misaligned resolution language (NLP score)",WARN),
        ("M06", "Daily Arb Loss Cap",    "Cumulative daily paper P&L cannot exceed configured drawdown",    ACCENT),
        ("M07", "Liquidity / VWAP",      "Depth must support 3× stake; VWAP slippage on both legs checked", ACCENT2),
        ("M08", "Spread Width",          "Kalshi orderbook spread must be within executable bounds",         OK),
        ("M09", "Kelly + CFTC Cap",      "Fractional Kelly sizing capped by CFTC notional position limit",  WARN),
    ]

    col_w = [42, 160, W - 80 - 212]
    row_h = 30
    tx = 30
    ty = H - 130

    for ri, (gate, name, desc, col) in enumerate(gates):
        rx = tx
        cells = [gate, name, desc]
        bgs = [HexColor("#1e2c42"), PANEL2, PANEL]
        for ci, (cell, cw, bg_c) in enumerate(zip(cells, col_w, bgs)):
            c.setFillColor(bg_c if ri % 2 == 0 else PANEL)
            c.rect(rx, ty - row_h, cw, row_h, fill=1, stroke=0)
            c.setFont("Helvetica-Bold" if ci < 2 else "Helvetica", 9)
            if ci == 0:
                c.setFillColor(col)
            elif ci == 1 and gate == "M01":
                c.setFillColor(DANGER)
            else:
                c.setFillColor(INK if ci == 2 else col)
            c.drawString(rx + 8, ty - row_h + 10, cell)
            rx += cw
        ty -= row_h

    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(MUTED)
    c.drawCentredString(W/2, 28, "First failure stops execution. Rejection reason is always logged to L4 audit stream.")
    slide_number(c, 15)

def slide_appendix_api(c):
    bg(c); accent_bar(c)
    eyebrow(c, "Appendix C — API Surface & Architecture", color=MUTED)
    headline(c, "Core services and endpoints.", size=24, y=H-88)

    endpoints = [
        ("GET", "/health",                   "System health — all dependency statuses",              OK),
        ("GET", "/api/arb/opportunities",    "Ranked arb list (canonical; bind UI here)",            ACCENT),
        ("GET", "/proposals",                "Active trade proposals with lifecycle state",           ACCENT2),
        ("GET", "/api/arb/opportunities/:id","Single opportunity detail + gate trace",               WARN),
        ("SSE", "/stream",                   "L4 observability stream — real-time operator events",  MUTED),
    ]

    col_w = [42, 210, W/2 - 40, 80]
    row_h = 28
    tx = 30
    ty = H - 130
    for method, path, desc, col in endpoints:
        c.setFillColor(PANEL2)
        c.roundRect(tx, ty - row_h, W - 60, row_h, 3, fill=1, stroke=0)
        c.setFillColor(col)
        c.roundRect(tx, ty - row_h, 42, row_h, 3, fill=1, stroke=0)
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(BG)
        c.drawCentredString(tx + 21, ty - row_h/2 - 4, method)
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(ACCENT2)
        c.drawString(tx + 50, ty - row_h + 10, path)
        c.setFont("Helvetica", 9)
        c.setFillColor(MUTED)
        c.drawString(tx + 260, ty - row_h + 10, desc)
        ty -= row_h + 4

    divider(c, 30, ty - 10, W - 60)

    services = [
        ("arb_engine.py",       "Scan, rank, persist opportunities"),
        ("settlement_auditor.py","Outcome resolution & precision"),
        ("backtest_engine.py",  "Historical performance replay"),
        ("risk_checks.py",      "M01–M09 gate implementations"),
        ("sqlite_store.py",     "All persistence (append-only)"),
        ("observability.py",    "L4 audit log + SSE stream"),
    ]
    sy = ty - 26
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(ACCENT)
    c.drawString(30, sy, "KEY MODULES")
    sy -= 16
    sw = (W - 80) / 3 - 8
    for i, (svc, sdesc) in enumerate(services):
        sx = 30 + (i % 3) * (sw + 12)
        if i % 3 == 0 and i > 0:
            sy -= 30
        c.setFillColor(PANEL2)
        c.roundRect(sx, sy - 22, sw, 26, 3, fill=1, stroke=0)
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(ACCENT2)
        c.drawString(sx + 8, sy - 8, svc)
        c.setFont("Helvetica", 7.5)
        c.setFillColor(MUTED)
        c.drawString(sx + 8, sy - 18, sdesc)

    slide_number(c, 16)

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

OUTPUT = str(Path(__file__).resolve().parent / "APEX_Autopilot_Pitch_Deck.pdf")

c = canvas.Canvas(OUTPUT, pagesize=(W, H))
c.setTitle("APEX Autopilot — Investor Pitch Deck")
c.setAuthor("Team Autopilot")
c.setSubject("Institutional Paper Trading Platform for Prediction Markets")

slides = [
    slide_title, slide_problem, slide_market, slide_solution, slide_product,
    slide_traction, slide_moat, slide_roadmap, slide_business, slide_competition,
    slide_team, slide_ask, slide_closing, slide_contact,
    slide_appendix_gates, slide_appendix_api,
]

for slide_fn in slides:
    slide_fn(c)
    c.showPage()

c.save()
print(f"Saved: {OUTPUT}")
