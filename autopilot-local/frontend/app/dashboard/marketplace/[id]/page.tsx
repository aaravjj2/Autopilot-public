"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { api, type PortfolioCard } from "@/lib/api";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { ApexAreaChart } from "@/components/chart/ApexChart";
import { PageHeader, Card, CardHeader, KpiCard, Tabs, Btn, Tag, EmptyState } from "@/components/terminal/ui";
import { formatCurrency, formatPercent, cn } from "@/lib/utils";
import { ArrowLeft } from "lucide-react";

export default function PortfolioDetailPage() {
  const params = useParams();
  const id = String(params.id ?? "");
  const [portfolio, setPortfolio] = useState<PortfolioCard | null>(null);
  const [period, setPeriod] = useState("1M");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    try {
      const p = await api.getPortfolio(id, period);
      setPortfolio(p);
    } catch (e) {
      console.error(e);
      setPortfolio(null);
    } finally {
      setLoading(false);
    }
  }, [id, period]);

  useEffect(() => {
    load();
  }, [load]);

  const toggleFollow = async () => {
    if (!portfolio) return;
    setBusy(true);
    try {
      if (portfolio.is_following) {
        await api.unfollowPortfolio(id);
      } else {
        await api.followPortfolio(id);
      }
      await load();
    } finally {
      setBusy(false);
    }
  };

  const chartData =
    portfolio?.performance?.map((pt) => ({
      time: new Date(pt.date).getTime(),
      value: pt.value,
    })) ?? [];

  return (
    <DashboardLayout>
      <PageHeader
        title={portfolio?.name ?? id}
        subtitle={
          <>
            <Link href="/dashboard/marketplace" className="btn" style={{ marginRight: 8, padding: "4px 10px" }}>
              <ArrowLeft size={14} style={{ marginRight: 4 }} />
              Marketplace
            </Link>
            {portfolio?.pilot_name} · {portfolio?.category}
          </>
        }
        actions={
          portfolio && (
            <Btn primary onClick={toggleFollow} disabled={busy}>
              {busy ? "…" : portfolio.is_following ? "Unfollow" : "Follow"}
            </Btn>
          )
        }
      />

      {loading ? (
        <EmptyState message="Loading portfolio…" />
      ) : !portfolio ? (
        <EmptyState message="Portfolio not found" />
      ) : (
        <>
          <div className="grid grid-kpi" style={{ marginBottom: 14, gridTemplateColumns: "repeat(4, 1fr)" }}>
            <KpiCard
              title="Return"
              value={formatPercent(portfolio.return_pct)}
              trend={portfolio.return_pct >= 0 ? "up" : "down"}
            />
            <KpiCard title="AUM" value={formatCurrency(portfolio.aum_usd)} />
            <KpiCard title="Sharpe" value={portfolio.sharpe_ratio != null ? String(portfolio.sharpe_ratio) : "—"} />
            <KpiCard
              title="Benchmark"
              value={
                portfolio.benchmark_return_pct != null
                  ? formatPercent(portfolio.benchmark_return_pct)
                  : "—"
              }
            />
          </div>

          <Card style={{ marginBottom: 14 }}>
            <CardHeader title="Performance" action={<Tabs items={["1W", "1M", "3M", "6M", "1Y"]} active={period} onChange={setPeriod} />} />
            {chartData.length > 0 ? (
              <ApexAreaChart data={chartData} height={240} />
            ) : (
              <div className="chart-area" style={{ height: 200 }} />
            )}
          </Card>

          <div className="grid grid-2">
            <Card>
              <CardHeader title="Holdings" />
              {portfolio.holdings && portfolio.holdings.length > 0 ? (
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Ticker</th>
                        <th>Weight</th>
                        <th>Shares</th>
                        <th>Price</th>
                        <th>Value</th>
                      </tr>
                    </thead>
                    <tbody>
                      {portfolio.holdings.map((h) => (
                        <tr key={h.ticker}>
                          <td className="mono">{h.ticker}</td>
                          <td>{h.weight_pct}%</td>
                          <td>{h.shares}</td>
                          <td>${h.price.toFixed(2)}</td>
                          <td>{formatCurrency(h.value_usd)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <EmptyState message="No holdings" />
              )}
            </Card>

            <Card>
              <CardHeader title="Recent trades" />
              {portfolio.trades && portfolio.trades.length > 0 ? (
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Time</th>
                        <th>Ticker</th>
                        <th>Side</th>
                        <th>Qty</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {portfolio.trades.map((t) => (
                        <tr key={t.id}>
                          <td style={{ fontSize: 11 }}>
                            {t.executed_at ? new Date(t.executed_at).toLocaleString() : "—"}
                          </td>
                          <td className="mono">{t.ticker}</td>
                          <td>
                            <Tag variant={t.side === "buy" ? "long" : "short"}>{t.side}</Tag>
                          </td>
                          <td>{t.qty}</td>
                          <td>{t.status}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <EmptyState message="No trades yet" />
              )}
            </Card>
          </div>

          {portfolio.is_following && (
            <div style={{ marginTop: 14 }}>
              <Btn
                onClick={async () => {
                  setBusy(true);
                  try {
                    await api.refreshPortfolio(id);
                    await load();
                  } finally {
                    setBusy(false);
                  }
                }}
                disabled={busy}
              >
                Refresh pilot holdings
              </Btn>
            </div>
          )}
        </>
      )}
    </DashboardLayout>
  );
}
