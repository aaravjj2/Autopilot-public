"use client";

import { useEffect, useState } from "react";
import { api, type TradeProposal } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { PageHeader, Card, CardHeader, KpiCard, Tag, Pipeline, EmptyState } from "@/components/terminal/ui";

export default function AutopilotPage() {
  const { opportunities, proposals, setProposals } = useAppStore();
  const [loading, setLoading] = useState(true);
  const [agentTimeline, setAgentTimeline] = useState<
    { agent: string; score: number; rationale: string }[]
  >([
    { agent: "Market", score: 7.2, rationale: "Uptrend / technical score strong (demo)" },
    { agent: "Fundamentals", score: 6.5, rationale: "Earnings catalyst weighted" },
    { agent: "Options", score: 7.0, rationale: "IV rank supports structure" },
    { agent: "PM", score: 6.8, rationale: "Neutral PM divergence" },
    { agent: "Judge", score: 6.9, rationale: "Synthesis → proposal pending risk" },
  ]);

  useEffect(() => {
    async function load() {
      try {
        const [p] = await Promise.all([api.getProposals()]);
        setProposals(p);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    load();
    const t = setInterval(load, 30000);
    return () => clearInterval(t);
  }, [setProposals]);

  return (
    <DashboardLayout>
      <PageHeader
        title="Autopilot Pipeline"
        subtitle="L0–L4 · Proposals · Risk gates"
        actions={<span className="pill live">Scheduler RUNNING</span>}
      />

      <Pipeline
        stages={[
          { id: "0", label: "L0", sub: "Ingest", active: true },
          { id: "1", label: "L1", sub: "Brain", active: true },
          { id: "2", label: "L2", sub: "Agents", active: true },
          { id: "3", label: "L3", sub: "Exec" },
          { id: "4", label: "L4", sub: "Obs" },
        ]}
      />

      <div className="grid grid-kpi" style={{ margin: "14px 0", gridTemplateColumns: "repeat(4, 1fr)" }}>
        <KpiCard title="Opportunities" value={String(opportunities.length)} />
        <KpiCard title="Proposals" value={String(proposals.length)} />
        <KpiCard title="Pending" value={String(proposals.filter((p) => p.status === "PENDING").length)} />
        <KpiCard title="High conv signals" value={String(opportunities.filter((o) => o.conviction >= 7).length)} />
      </div>

      <div className="grid grid-2">
        <Card>
          <CardHeader title="Active Proposals" />
          {loading ? (
            <EmptyState message="Loading…" />
          ) : proposals.length === 0 ? (
            <EmptyState message="No proposals" />
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Symbol</th>
                    <th>Dir</th>
                    <th>Conv</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {proposals.map((p: TradeProposal) => (
                    <tr key={p.id}>
                      <td>{p.symbol}</td>
                      <td>
                        <Tag variant={p.direction === "LONG" ? "long" : "short"}>{p.direction}</Tag>
                      </td>
                      <td>{p.conviction.toFixed(1)}</td>
                      <td>
                        <Tag variant="neutral">{p.status}</Tag>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
        <Card>
          <CardHeader title="L2 agent votes" />
          <ul style={{ listStyle: "none", fontSize: 13, lineHeight: 1.8 }}>
            {agentTimeline.map((row) => (
              <li
                key={row.agent}
                style={{
                  padding: "8px 0",
                  borderBottom: "1px solid var(--border)",
                  display: "flex",
                  justifyContent: "space-between",
                  gap: 8,
                }}
              >
                <span>
                  <strong>{row.agent}</strong>
                  <span style={{ color: "var(--text-muted)", marginLeft: 8, fontSize: 11 }}>
                    {row.rationale}
                  </span>
                </span>
                <Tag variant={row.score >= 7 ? "long" : "neutral"}>{row.score.toFixed(1)}</Tag>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <Card style={{ marginTop: 14 }}>
        <CardHeader title="Risk checks (14-gate stack)" />
        <ul style={{ listStyle: "none", fontSize: 13, lineHeight: 2, color: "var(--text-muted)" }}>
          <li>✓ R01 Paper trading only</li>
          <li>✓ R02 Position size cap</li>
          <li>✓ R06 Earnings blackout</li>
          <li>○ R09 Dexter adversarial gate</li>
          <li>✓ M07 Liquidity (arb)</li>
        </ul>
      </Card>
    </DashboardLayout>
  );
}
