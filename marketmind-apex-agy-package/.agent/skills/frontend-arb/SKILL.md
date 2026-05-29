---
name: frontend-arb
description: >
  Use this skill when building or modifying the Next.js arb-radar page, the live
  opportunity table, settlement badges, resolution countdown timers, and paper trade
  buttons. Also covers the analytics tab backtest integration. Trigger for any
  autopilot-local/frontend work on arb-radar or ThesisCard.
compatibility: Antigravity CLI (agy), Claude Code, Gemini CLI
---

# Frontend Arb Radar Skill

## Arb Radar Page

```tsx
// autopilot-local/frontend/app/dashboard/arb-radar/page.tsx
"use client";

import { useEffect, useState } from "react";
import { ThesisCard } from "@/components/ThesisCard";

interface ArbRow {
  id: string;
  kalshi_ticker: string;
  poly_market_id: string;
  question: string;
  net_edge: number;
  gross_spread: number;
  kalshi_yes_ask: number;
  poly_no_ask: number;
  settlement_match_score: number;
  settlement_flags: string[];
  detection_ts: string;
  resolution_ts: string | null;
  volume_kalshi: number;
  volume_poly: number;
}

function SettlementBadge({ score, flags }: { score: number; flags: string[] }) {
  const label = score >= 0.75 ? "SAFE" : score >= 0.45 ? "CAUTION" : "BLOCK";
  const cls   = score >= 0.75
    ? "bg-green-100 text-green-700"
    : score >= 0.45
    ? "bg-yellow-100 text-yellow-700"
    : "bg-red-100 text-red-700";
  return (
    <div className="flex items-center gap-1">
      <span className={`text-xs font-semibold px-2 py-0.5 rounded ${cls}`}>{label}</span>
      {flags.length > 0 && (
        <span className="text-xs text-orange-600" title={flags.join(", ")}>⚠ {flags.length}</span>
      )}
    </div>
  );
}

function ResolutionCountdown({ ts }: { ts: string | null }) {
  const [text, setText] = useState("—");
  useEffect(() => {
    if (!ts) return;
    const update = () => {
      const diff = new Date(ts).getTime() - Date.now();
      if (diff <= 0) { setText("Resolved"); return; }
      const d = Math.floor(diff / 86400000);
      const h = Math.floor((diff % 86400000) / 3600000);
      setText(d > 0 ? `${d}d ${h}h` : `${h}h`);
    };
    update();
    const interval = setInterval(update, 60_000);
    return () => clearInterval(interval);
  }, [ts]);
  return <span className="text-xs text-gray-500">{text}</span>;
}

export default function ArbRadarPage() {
  const [opps, setOpps]       = useState<ArbRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeThesis, setActiveThesis] = useState<string | null>(null);
  const [submitting, setSubmitting]     = useState<string | null>(null);

  const fetchOpps = () => {
    setLoading(true);
    fetch("/api/arb/opportunities?limit=50&min_edge=0.02")
      .then(r => r.json())
      .then(data => { setOpps(data); setLoading(false); })
      .catch(() => setLoading(false));
  };

  useEffect(() => {
    fetchOpps();
    const interval = setInterval(fetchOpps, 5 * 60 * 1000); // refresh every 5 min
    return () => clearInterval(interval);
  }, []);

  const submitPaperTrade = async (opp: ArbRow) => {
    setSubmitting(opp.id);
    try {
      const res = await fetch(`/api/arb/${opp.id}/paper-trade`, { method: "POST" });
      const data = await res.json();
      alert(data.message || "Paper trade submitted");
    } catch (e) {
      alert("Failed to submit paper trade");
    } finally {
      setSubmitting(null);
    }
  };

  if (loading) return <div className="p-8 text-sm text-gray-500">Scanning markets…</div>;

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Arb Radar</h1>
        <button
          onClick={fetchOpps}
          className="text-sm px-3 py-1.5 rounded bg-teal-600 text-white hover:bg-teal-700"
        >
          Refresh
        </button>
      </div>

      <p className="text-xs text-gray-500">
        {opps.length} opportunities with net edge ≥ 2¢ · Updates every 5 min
      </p>

      <div className="overflow-x-auto">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="border-b text-xs text-gray-500 text-left">
              <th className="py-2 pr-4 font-medium">Question</th>
              <th className="py-2 pr-4 font-medium">Net Edge</th>
              <th className="py-2 pr-4 font-medium">Legs</th>
              <th className="py-2 pr-4 font-medium">Settlement</th>
              <th className="py-2 pr-4 font-medium">Resolves</th>
              <th className="py-2 pr-4 font-medium">Volume</th>
              <th className="py-2 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {opps
              .sort((a, b) => b.net_edge - a.net_edge)
              .map(opp => (
                <>
                  <tr key={opp.id} className="border-b hover:bg-gray-50">
                    <td className="py-2 pr-4 max-w-xs">
                      <p className="font-medium text-gray-900 truncate" title={opp.question}>
                        {opp.question.length > 60 ? opp.question.slice(0, 60) + "…" : opp.question}
                      </p>
                      <p className="text-xs text-gray-400">{opp.kalshi_ticker}</p>
                    </td>
                    <td className="py-2 pr-4">
                      <span className={`font-bold ${opp.net_edge >= 0.05 ? "text-teal-700" : "text-gray-700"}`}>
                        ${opp.net_edge.toFixed(3)}
                      </span>
                      <p className="text-xs text-gray-400">gross ${opp.gross_spread.toFixed(3)}</p>
                    </td>
                    <td className="py-2 pr-4 font-mono text-xs">
                      <div>K YES @${opp.kalshi_yes_ask.toFixed(2)}</div>
                      <div>P NO @${opp.poly_no_ask.toFixed(2)}</div>
                    </td>
                    <td className="py-2 pr-4">
                      <SettlementBadge
                        score={opp.settlement_match_score}
                        flags={opp.settlement_flags}
                      />
                    </td>
                    <td className="py-2 pr-4">
                      <ResolutionCountdown ts={opp.resolution_ts} />
                    </td>
                    <td className="py-2 pr-4 text-xs text-gray-500">
                      K:${(opp.volume_kalshi / 1000).toFixed(0)}k P:${(opp.volume_poly / 1000).toFixed(0)}k
                    </td>
                    <td className="py-2 space-x-2">
                      <button
                        onClick={() => setActiveThesis(activeThesis === opp.id ? null : opp.id)}
                        className="text-xs px-2 py-1 rounded border border-blue-300 text-blue-600 hover:bg-blue-50"
                      >
                        AI Thesis
                      </button>
                      <button
                        onClick={() => submitPaperTrade(opp)}
                        disabled={submitting === opp.id || opp.settlement_match_score < 0.45}
                        className="text-xs px-2 py-1 rounded bg-teal-600 text-white hover:bg-teal-700 disabled:opacity-40"
                      >
                        {submitting === opp.id ? "…" : "Paper Trade"}
                      </button>
                    </td>
                  </tr>
                  {activeThesis === opp.id && (
                    <tr key={`${opp.id}-thesis`}>
                      <td colSpan={7} className="pb-3 pt-1 px-0">
                        <div className="ml-4">
                          <ThesisCard arbId={opp.id} autoStart />
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

---

## Backend API Endpoints to Add

```python
# autopilot-local/backend/main.py

@app.get("/api/arb/opportunities")
async def list_arb_opportunities(limit: int = 50, min_edge: float = 0.02):
    """Return latest detected arb opportunities."""
    store = SQLiteStore(get_settings().sqlite_path)
    opps  = store.get_recent_arb_opportunities(limit=limit, min_edge=min_edge)
    return [vars(o) for o in opps]  # or use .to_dict() if you add that method

@app.post("/api/arb/{arb_id}/paper-trade")
async def submit_arb_paper_trade(arb_id: str):
    settings = get_settings()
    store    = SQLiteStore(settings.sqlite_path)
    opp      = store.get_arb_opportunity(arb_id)
    if not opp:
        raise HTTPException(404, "Opportunity not found")
    # Trigger paper submission via engine
    from apex.layers.l3.execution import ExecutionService
    # ... wire execution service
    return {"message": f"Paper trade submitted for {arb_id}", "status": "ok"}
```

---

## Navigation Update

Add link to `autopilot-local/frontend/components/Nav.tsx`:

```tsx
{ href: "/dashboard/arb-radar", label: "Arb Radar", icon: "radar" }
```
