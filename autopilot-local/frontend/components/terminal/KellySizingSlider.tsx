"use client";

/** Interactive Kelly sizing visualizer (Week 6 / master plan). */

import { cn } from "@/lib/utils";

export function KellySizingSlider({
  edgePct,
  kellyPct,
  vix,
  vixMultiplier,
  alpha = 0.25,
}: {
  edgePct: number;
  kellyPct: number;
  vix: number;
  vixMultiplier: number;
  alpha?: number;
}) {
  const pct = Math.min(100, Math.max(0, kellyPct * 100));
  return (
    <div data-testid="kelly-slider" className="card" style={{ padding: 14 }}>
      <div className="card-title">Fractional Kelly · α={alpha}</div>
      <div style={{ display: "flex", gap: 16, marginTop: 10, alignItems: "center" }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 6 }}>
            Edge {edgePct.toFixed(1)}% → Suggested {pct.toFixed(1)}%
          </div>
          <div
            style={{
              height: 10,
              background: "var(--surface-2)",
              borderRadius: 5,
              overflow: "hidden",
            }}
          >
            <div
              className={cn(pct > 15 ? "kpi-up" : "")}
              style={{
                width: `${pct}%`,
                height: "100%",
                background: "var(--green)",
                transition: "width 0.3s",
              }}
            />
          </div>
        </div>
        <div style={{ textAlign: "right", fontSize: 12 }}>
          <div>
            VIX <span className="mono">{vix.toFixed(1)}</span>
          </div>
          <div style={{ color: "var(--text-muted)" }}>
            dampener <span className="mono">{vixMultiplier.toFixed(3)}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
