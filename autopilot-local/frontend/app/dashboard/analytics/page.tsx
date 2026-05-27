"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { ApiErrorBanner } from "@/components/terminal/ApiErrorBanner";
import { ApexAreaChart } from "@/components/chart/ApexChart";
import { PageHeader, Card, CardHeader, KpiCard, Tabs, EmptyState } from "@/components/terminal/ui";
import { BacktestTab } from "./BacktestTab";
import { MlEngineTab } from "./MlEngineTab";
import { getApexDirectUrl } from "@/lib/backend-urls";

export default function AnalyticsPage() {
  const { account } = useAppStore();
  const [tab, setTab] = useState("Performance");
  const [history, setHistory] = useState<Array<{ time: number; value: number }>>([]);
  const [perf, setPerf] = useState<Record<string, unknown> | null>(null);
  const [perfError, setPerfError] = useState<string | null>(null);
  const [signals, setSignals] = useState<{
    by_source: Record<string, { count: number; avg_conviction: number; approval_rate: number }>;
    by_conviction: Record<string, { count: number; approval_rate: number }>;
  } | null>(null);
  const [signalsError, setSignalsError] = useState<string | null>(null);

  const loadPerformance = useCallback(async () => {
    setPerfError(null);
    try {
      const h = await api.getAccountHistory(60);
      if (Array.isArray(h) && h.length) {
        setHistory(
          h.map((row: { time?: number; equity?: number }) => ({
            time: row.time || Date.now(),
            value: row.equity || 0,
          }))
        );
      } else if (account?.equity) {
        setHistory([{ time: Date.now(), value: account.equity }]);
      } else {
        setHistory([]);
      }
      setPerf(await api.getPerformanceAnalytics());
    } catch (e) {
      setPerfError(e instanceof Error ? e.message : "Performance API failed");
      setPerf(null);
    }
  }, [account?.equity]);

  const loadSignals = useCallback(async () => {
    setSignalsError(null);
    try {
      setSignals(await api.getSignalQuality());
    } catch (e) {
      setSignalsError(e instanceof Error ? e.message : "Signal quality API failed");
      setSignals(null);
    }
  }, []);

  useEffect(() => {
    if (tab === "Performance") loadPerformance();
    if (tab === "Signals") loadSignals();
  }, [tab, loadPerformance, loadSignals]);

  return (
    <DashboardLayout>
      <PageHeader
        title="Analytics"
        subtitle="Portfolio performance · Arb backtest · ML engine · Signal quality"
      />

      <Tabs
        testId="analytics-tabs"
        items={["Performance", "Arb Backtest", "ML Engine", "Signals"]}
        active={tab}
        onChange={setTab}
      />

      {tab === "Performance" && (
        <>
          {perfError && (
            <ApiErrorBanner message={perfError} hint={`APEX analytics at ${getApexDirectUrl()}`} />
          )}
          <div className="grid grid-kpi" style={{ margin: "14px 0", gridTemplateColumns: "repeat(4, 1fr)" }}>
            <KpiCard title="Sharpe" value={String((perf?.sharpe_ratio as number)?.toFixed(2) ?? "—")} />
            <KpiCard
              title="Win rate"
              value={perf?.win_rate != null ? `${((perf.win_rate as number) * 100).toFixed(0)}%` : "—"}
            />
            <KpiCard
              title="Max DD"
              value={perf?.max_drawdown_pct != null ? `${(perf.max_drawdown_pct as number).toFixed(1)}%` : "—"}
            />
            <KpiCard title="Trades" value={String(perf?.total_trades ?? "—")} />
          </div>
          <Card>
            <CardHeader title="Equity · 60D" />
            {history.length > 0 ? (
              <ApexAreaChart data={history} height={260} />
            ) : (
              <EmptyState message="No equity history — refresh engine cache on Overview" />
            )}
          </Card>
        </>
      )}

      {tab === "Arb Backtest" && (
        <Card style={{ marginTop: 14 }}>
          <BacktestTab />
        </Card>
      )}

      {tab === "ML Engine" && (
        <div style={{ marginTop: 14 }}>
          <MlEngineTab />
        </div>
      )}

      {tab === "Signals" && (
        <Card style={{ marginTop: 14 }}>
          <CardHeader title="Signal quality by source" />
          {signalsError && (
            <ApiErrorBanner message={signalsError} hint="Requires audit events in APEX SQLite" />
          )}
          {!signals && !signalsError && <EmptyState message="Loading signal stats…" />}
          {signals && Object.keys(signals.by_source).length === 0 && (
            <EmptyState message="No signal events yet — run Autopilot or Live Feed" />
          )}
          {signals && Object.keys(signals.by_source).length > 0 && (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Source</th>
                    <th>Count</th>
                    <th>Avg conviction</th>
                    <th>Approval rate</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(signals.by_source).map(([src, s]) => (
                    <tr key={src}>
                      <td>{src}</td>
                      <td>{String(s.count ?? "—")}</td>
                      <td>{Number(s.avg_conviction ?? 0).toFixed(2)}</td>
                      <td>{(Number(s.approval_rate ?? 0) * 100).toFixed(0)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}
    </DashboardLayout>
  );
}
