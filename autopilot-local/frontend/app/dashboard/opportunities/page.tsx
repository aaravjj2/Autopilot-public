"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { PageHeader, Card, CardHeader, KpiCard, Tag, EmptyState } from "@/components/terminal/ui";

export default function OpportunitiesPage() {
  const { opportunities, setOpportunities } = useAppStore();
  const [loading, setLoading] = useState(true);
  const [minConviction, setMinConviction] = useState(0);
  const [search, setSearch] = useState("");

  useEffect(() => {
    async function load() {
      try {
        setOpportunities(await api.getOpportunities());
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    load();
    const t = setInterval(load, 30000);
    return () => clearInterval(t);
  }, [setOpportunities]);

  const filtered = opportunities
    .filter((o) => o.conviction >= minConviction)
    .filter((o) => !search || o.symbol.toLowerCase().includes(search.toLowerCase()))
    .sort((a, b) => b.conviction - a.conviction);

  return (
    <DashboardLayout>
      <PageHeader title="Opportunity Signals" subtitle="Engine-scored · PM divergence · Real audit data" />

      <div className="grid grid-kpi" style={{ marginBottom: 14, gridTemplateColumns: "repeat(4, 1fr)" }}>
        <KpiCard title="Total" value={String(opportunities.length)} />
        <KpiCard title="Long" value={String(opportunities.filter((o) => o.direction === "LONG").length)} />
        <KpiCard title="High conv (≥7)" value={String(opportunities.filter((o) => o.conviction >= 7).length)} />
        <KpiCard
          title="Avg conviction"
          value={
            opportunities.length
              ? (opportunities.reduce((s, o) => s + o.conviction, 0) / opportunities.length).toFixed(1)
              : "0"
          }
        />
      </div>

      <Card style={{ marginBottom: 14 }}>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 12 }}>
          <input
            className="search-box"
            style={{ flex: 1, minWidth: 160, margin: 0 }}
            placeholder="Filter symbol…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <label style={{ fontSize: 12, color: "var(--text-muted)", display: "flex", alignItems: "center", gap: 8 }}>
            Min conviction
            <input
              type="number"
              min={0}
              max={10}
              step={0.5}
              value={minConviction}
              onChange={(e) => setMinConviction(parseFloat(e.target.value) || 0)}
              style={{ width: 64, padding: "6px 8px", borderRadius: 6, border: "1px solid var(--border)", background: "var(--bg-base)" }}
            />
          </label>
        </div>
        {loading ? (
          <EmptyState message="Loading…" />
        ) : filtered.length === 0 ? (
          <EmptyState message="No opportunities match filters" />
        ) : (
          <div className="table-wrap" style={{ maxHeight: "60vh" }}>
            <table>
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Dir</th>
                  <th>Instrument</th>
                  <th>Tech</th>
                  <th>Fund</th>
                  <th>PM</th>
                  <th>Conv</th>
                  <th>R:R</th>
                  <th>Catalyst</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((o) => (
                  <tr key={`${o.symbol}-${o.direction}`}>
                    <td className="mono" style={{ fontWeight: 600 }}>
                      {o.symbol}
                    </td>
                    <td>
                      <Tag variant={o.direction === "LONG" ? "long" : o.direction === "SHORT" ? "short" : "neutral"}>
                        {o.direction}
                      </Tag>
                    </td>
                    <td>{o.instrument}</td>
                    <td>{o.technical_score.toFixed(1)}</td>
                    <td>{o.fundamental_score.toFixed(1)}</td>
                    <td>{o.pm_signal}</td>
                    <td>
                      <strong>{o.conviction.toFixed(1)}</strong>
                    </td>
                    <td>{o.risk_reward.toFixed(1)}</td>
                    <td style={{ maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis" }}>
                      {o.catalyst}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </DashboardLayout>
  );
}
