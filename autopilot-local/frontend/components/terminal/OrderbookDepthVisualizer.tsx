"use client";

/** L2 depth bars for arb venues (Week 2 UI). */

type Level = [number, number];

export function OrderbookDepthVisualizer({
  yes = [],
  no = [],
  maxLevels = 5,
}: {
  yes?: Level[];
  no?: Level[];
  maxLevels?: number;
}) {
  const maxVol = Math.max(
    1,
    ...[...yes, ...no].slice(0, maxLevels).map(([, q]) => q)
  );

  const renderSide = (label: string, levels: Level[], color: string) => (
    <div style={{ flex: 1 }}>
      <div className="card-title" style={{ marginBottom: 6 }}>
        {label}
      </div>
      {levels.slice(0, maxLevels).map(([price, qty], i) => (
        <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
          <span className="mono" style={{ width: 48, fontSize: 11 }}>
            {price.toFixed(2)}
          </span>
          <div
            style={{
              flex: 1,
              height: 8,
              background: "var(--surface-2)",
              borderRadius: 4,
              overflow: "hidden",
            }}
          >
            <div
              style={{
                width: `${(qty / maxVol) * 100}%`,
                height: "100%",
                background: color,
              }}
            />
          </div>
          <span className="mono" style={{ fontSize: 10, color: "var(--text-muted)" }}>
            {qty}
          </span>
        </div>
      ))}
    </div>
  );

  return (
    <div data-testid="orderbook-depth" style={{ display: "flex", gap: 16, padding: 12 }}>
      {renderSide("YES", yes, "var(--green)")}
      {renderSide("NO", no, "var(--red)")}
    </div>
  );
}
