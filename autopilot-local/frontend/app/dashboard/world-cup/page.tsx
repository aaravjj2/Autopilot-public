"use client";

import { useCallback, useEffect, useState } from "react";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { ApiErrorBanner } from "@/components/terminal/ApiErrorBanner";
import { PageHeader, Card, CardHeader, KpiCard, Btn, EmptyState } from "@/components/terminal/ui";
import { predictionMarkets, type WorldCupOpportunity, type WorldCupStatus } from "@/lib/predictionMarkets";
import { getApexDirectUrl } from "@/lib/backend-urls";

export default function WorldCupPage() {
  const [status, setStatus] = useState<WorldCupStatus | null>(null);
  const [opps, setOpps] = useState<WorldCupOpportunity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [cycleMsg, setCycleMsg] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [st, rows] = await Promise.all([
        predictionMarkets.getWorldCupStatus(),
        predictionMarkets.getWorldCupOpportunities(),
      ]);
      setStatus(st);
      setOpps(rows);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load World Cup data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, 60_000);
    return () => clearInterval(t);
  }, [load]);

  const runCycle = async () => {
    setRunning(true);
    setCycleMsg(null);
    try {
      const res = await predictionMarkets.runWorldCupCycle();
      setCycleMsg(
        `Cycle: ${res.discovery_count ?? 0} discovered · ${res.paper_trade_count ?? 0} paper trades`
      );
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Cycle failed");
    } finally {
      setRunning(false);
    }
  };

  return (
    <DashboardLayout>
      <PageHeader
        title="FIFA World Cup 2026"
        subtitle="Elo model vs Kalshi / Polymarket prices · paper execution only"
        actions={
          <>
            <Btn onClick={runCycle} disabled={running}>
              {running ? "Running…" : "Run World Cup agent"}
            </Btn>
            <Btn onClick={load} disabled={loading} style={{ marginLeft: 8 }}>
              Refresh
            </Btn>
          </>
        }
      />

      <div
        className="pill"
        style={{
          marginBottom: 12,
          padding: "10px 14px",
          background: "rgba(234, 179, 8, 0.12)",
          border: "1px solid rgba(234, 179, 8, 0.35)",
          fontSize: 13,
        }}
      >
        Paper simulation — trades are logged in APEX only. Reference markets on{" "}
        <a
          href="https://kalshi.com/category/sports/soccer/fifa-world-cup"
          target="_blank"
          rel="noreferrer"
        >
          Kalshi FIFA World Cup
        </a>
        .
      </div>

      {error && <ApiErrorBanner message={error} hint={`APEX at ${getApexDirectUrl()}`} />}
      {cycleMsg && <p style={{ fontSize: 13, color: "var(--green)", marginBottom: 12 }}>{cycleMsg}</p>}

      <div className="grid grid-kpi" style={{ marginBottom: 14, gridTemplateColumns: "repeat(4, 1fr)" }}>
        <KpiCard title="Cached opps" value={String(status?.opportunities_cached ?? "—")} />
        <KpiCard title="Min model edge" value={String(status?.min_model_edge ?? "—")} />
        <KpiCard
          title="Top model edge"
          value={
            opps[0]?.model_edge != null ? `${(Number(opps[0].model_edge) * 100).toFixed(1)}%` : "—"
          }
        />
        <KpiCard title="Mode" value={status?.execution_mode ?? "paper_simulated"} />
      </div>

      <Card>
        <CardHeader title="Model vs market" subtitle="Sorted by final_score" />
        {loading && <EmptyState message="Loading…" />}
        {!loading && opps.length === 0 && (
          <EmptyState message="No World Cup opportunities — run discover or agent cycle" />
        )}
        {opps.length > 0 && (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Venue</th>
                  <th>Question</th>
                  <th>Market</th>
                  <th>Fair</th>
                  <th>Edge</th>
                  <th>Net arb</th>
                </tr>
              </thead>
              <tbody>
                {opps.slice(0, 40).map((o) => (
                  <tr key={String(o.id)}>
                    <td>{o.venue}</td>
                    <td style={{ maxWidth: 280 }}>{o.question}</td>
                    <td className="mono">{(Number(o.market_yes_ask) * 100).toFixed(1)}%</td>
                    <td className="mono">{(Number(o.fair_prob) * 100).toFixed(1)}%</td>
                    <td className="mono">{(Number(o.model_edge) * 100).toFixed(1)}%</td>
                    <td className="mono">
                      {o.net_edge != null ? `${(Number(o.net_edge) * 100).toFixed(1)}%` : "—"}
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
