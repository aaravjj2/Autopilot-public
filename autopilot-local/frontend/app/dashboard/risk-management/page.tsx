"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { ApiErrorBanner } from "@/components/terminal/ApiErrorBanner";
import { KellySizingSlider } from "@/components/terminal/KellySizingSlider";
import { PageHeader, Card, CardHeader, KpiCard, EmptyState } from "@/components/terminal/ui";
import { getApexDirectUrl } from "@/lib/backend-urls";
import { formatCurrency } from "@/lib/utils";

type RiskMetrics = {
  vix: number;
  kelly_alpha: number;
  var: {
    var_99_usd: number;
    cvar_99_usd: number;
    var_99_pct: number;
    paths: number;
    max_drawdown_p99_pct: number;
  };
  cftc: {
    limit_usd: number;
    breach_count: number;
    positions: Array<{
      contract: string;
      notional_usd: number;
      utilization_pct: number;
      headroom_usd: number;
      breached: boolean;
    }>;
  };
  kelly_samples: Array<{
    id: string;
    ticker: string;
    suggested_fraction: number;
    vix_multiplier: number;
  }>;
  account_equity: number;
};

export default function RiskManagementPage() {
  const [data, setData] = useState<RiskMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const raw = await api.getRiskMetrics();
      setData(raw as RiskMetrics);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Risk API unavailable");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, 30_000);
    return () => clearInterval(t);
  }, [load]);

  const topKelly = data?.kelly_samples?.[0];

  return (
    <DashboardLayout>
      <PageHeader
        title="Risk Management"
        subtitle="Monte Carlo VaR · CFTC limits · VIX-dampened Kelly sizing"
        actions={
          <button type="button" className="btn" data-testid="risk-refresh" onClick={load}>
            ↻ Refresh
          </button>
        }
      />

      {error && (
        <ApiErrorBanner message={`Risk API error: ${error}`} hint={`Check APEX at ${getApexDirectUrl()}`} />
      )}

      {loading && !data && !error && <EmptyState message="Loading risk metrics…" />}

      {data && (
        <>
          <div className="grid grid-kpi" style={{ marginBottom: 14, gridTemplateColumns: "repeat(5, 1fr)" }}>
            <KpiCard title="VIX" value={data.vix.toFixed(1)} subValue="CBOE dampener λ" />
            <KpiCard
              title="VaR 99%"
              value={formatCurrency(data.var.var_99_usd)}
              subValue={`${data.var.var_99_pct.toFixed(2)}% · ${data.var.paths.toLocaleString()} paths`}
            />
            <KpiCard
              title="CVaR 99%"
              value={formatCurrency(data.var.cvar_99_usd)}
              subValue="Expected shortfall"
            />
            <KpiCard
              title="Max DD (p99)"
              value={`${data.var.max_drawdown_p99_pct.toFixed(2)}%`}
              subValue="1-day horizon"
            />
            <KpiCard
              title="CFTC breaches"
              value={String(data.cftc.breach_count)}
              subValue={`Limit ${formatCurrency(data.cftc.limit_usd)}`}
              trend={data.cftc.breach_count > 0 ? "down" : "up"}
            />
          </div>

          {topKelly && (
            <KellySizingSlider
              edgePct={(topKelly.suggested_fraction / topKelly.vix_multiplier) * 100}
              kellyPct={topKelly.suggested_fraction * 100}
              vix={data.vix}
              vixMultiplier={topKelly.vix_multiplier}
              alpha={data.kelly_alpha}
            />
          )}

          <Card style={{ marginTop: 14 }}>
            <CardHeader title="CFTC positional limits" />
            <div className="table-wrap" style={{ maxHeight: 360 }}>
              <table>
                <thead>
                  <tr>
                    <th>Contract</th>
                    <th>Notional</th>
                    <th>Utilization</th>
                    <th>Headroom</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {data.cftc.positions.length === 0 ? (
                    <tr>
                      <td colSpan={5} style={{ color: "var(--text-muted)", padding: 16 }}>
                        No tracked exposures — open positions sync on refresh
                      </td>
                    </tr>
                  ) : (
                    data.cftc.positions.map((p) => (
                      <tr key={p.contract} data-testid={`cftc-row-${p.contract}`}>
                        <td className="mono">{p.contract}</td>
                        <td>{formatCurrency(p.notional_usd)}</td>
                        <td>{p.utilization_pct.toFixed(1)}%</td>
                        <td>{formatCurrency(p.headroom_usd)}</td>
                        <td>
                          <span className={p.breached ? "pill" : "pill live"}>
                            {p.breached ? "BREACH" : "OK"}
                          </span>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </Card>

          <Card style={{ marginTop: 14 }}>
            <CardHeader title="Kelly samples (top arbs)" />
            {data.kelly_samples.length === 0 ? (
              <EmptyState message="No arb Kelly samples — populate Arb Radar first" />
            ) : (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Ticker</th>
                      <th>Suggested %</th>
                      <th>VIX mult</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.kelly_samples.map((k) => (
                      <tr key={k.id}>
                        <td className="mono">{k.ticker}</td>
                        <td>{(k.suggested_fraction * 100).toFixed(2)}%</td>
                        <td className="mono">{k.vix_multiplier.toFixed(4)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </>
      )}
    </DashboardLayout>
  );
}
