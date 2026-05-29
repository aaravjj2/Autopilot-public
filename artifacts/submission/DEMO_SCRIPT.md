# APEX Autopilot — Demo video narration script (~3 min)

Use with `APEX_Autopilot_Demo.mp4`. Adjust pace to match recording.

| Time | Visual | Say |
|------|--------|-----|
| 0:00 | Title card | "This is APEX Autopilot — an institutional paper-trading platform for prediction markets." |
| 0:10 | Overview | "Operators get a Bloomberg-style command center: live health, signals, and paper order controls — all in one shell." |
| 0:25 | Arb Radar | "Arb Radar ranks cross-venue opportunities between Kalshi and Polymarket — net edge, confidence, and settlement alignment on every row." |
| 0:40 | Signals | "Opportunity Signals show what the engine is surfacing before anything becomes a trade proposal." |
| 0:55 | Autopilot | "The Autopilot pipeline turns scored opportunities into proposals — each step logged, each leg subject to risk gates." |
| 1:10 | Risk | "Risk Management is not an afterthought. Paper mode is enforced first — M01 — then edge, volume, settlement, loss caps, and liquidity checks." |
| 1:25 | Hive-Mind | "The AI Hive-Mind layer adds multi-agent thesis and verdicts — BUY, SKIP, WAIT — with bounded budgets and soft-fail when intel services are offline." |
| 1:40 | Live Feed | "Live Feed streams audit events so you can replay what the system saw and why it acted." |
| 1:50 | Settings | "Settings expose paper-only defaults and operator controls — autonomy with discipline, not a black box." |
| 2:00 | Sidebar nav | "Navigation is built for speed: radar, pipeline, risk — one click each." |
| 2:15 | API docs | "Under the hood, FastAPI exposes health, arb opportunities, proposals, and intelligence endpoints — everything the terminal consumes." |
| 2:30 | Outro | "APEX Autopilot: paper-only, gate-first, fully auditable. Code and docs on GitHub — Autopilot-public." |

## Live stats to mention (verify before recording)

Run:
```bash
curl -s http://127.0.0.1:8000/api/arb/opportunities | python3 -c "import sys,json;d=json.load(sys.stdin);print(len(d) if isinstance(d,list) else 'check')"
```

Mention the live count from `api-arb-sample.json` in this package.
