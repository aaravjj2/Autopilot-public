"use client";

import { useCallback, useEffect, useState } from "react";
import { api, type PortfolioCard as PortfolioType, type DashboardData } from "@/lib/api";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { ApiErrorBanner } from "@/components/terminal/ApiErrorBanner";
import { PortfolioCard } from "@/components/PortfolioCard";
import { PageHeader, Card, CardHeader, KpiCard, Tabs, Btn, EmptyState } from "@/components/terminal/ui";
import { getApexApiUrl } from "@/lib/backend-urls";
import { formatCurrency, cn } from "@/lib/utils";

export default function MarketplacePage() {
  const [portfolios, setPortfolios] = useState<PortfolioType[]>([]);
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [period, setPeriod] = useState("1M");
  const [sort, setSort] = useState("return");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [list, dash] = await Promise.all([
        api.listPortfolios({ period, sort }),
        api.getDashboard(),
      ]);
      setPortfolios(list);
      setDashboard(dash);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Marketplace API unavailable");
      setPortfolios([]);
      setDashboard(null);
    } finally {
      setLoading(false);
    }
  }, [period, sort]);

  useEffect(() => {
    load();
  }, [load]);

  const handleFollow = async (id: string) => {
    setActionError(null);
    try {
      await api.followPortfolio(id);
      await load();
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Follow failed");
    }
  };

  const handleUnfollow = async (id: string) => {
    setActionError(null);
    try {
      await api.unfollowPortfolio(id);
      await load();
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Unfollow failed");
    }
  };

  const handleRefreshAll = async () => {
    setRefreshing(true);
    setActionError(null);
    try {
      await api.refreshAll();
      await load();
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Refresh failed");
    } finally {
      setRefreshing(false);
    }
  };

  const followed = dashboard?.followed_portfolios ?? [];

  return (
    <DashboardLayout>
      <PageHeader
        title="Copy Trading Marketplace"
        subtitle="Follow Alpaca pilot portfolios · paper mirror trades (equities only)"
        actions={
          <Btn primary onClick={handleRefreshAll} disabled={refreshing}>
            {refreshing ? "Refreshing…" : "Refresh all"}
          </Btn>
        }
      />

      {error && (
        <ApiErrorBanner
          message={error}
          hint={`Unified backend at ${getApexApiUrl()}`}
        />
      )}
      {actionError && <ApiErrorBanner message={actionError} />}

      {dashboard && (
        <div className="grid grid-kpi" style={{ marginBottom: 14, gridTemplateColumns: "repeat(4, 1fr)" }}>
          <KpiCard title="Equity" value={formatCurrency(dashboard.account.equity)} />
          <KpiCard title="Cash" value={formatCurrency(dashboard.account.cash)} />
          <KpiCard
            title="Unrealized P&amp;L"
            value={formatCurrency(dashboard.account.unrealized_pl)}
            trend={dashboard.account.unrealized_pl >= 0 ? "up" : "down"}
          />
          <KpiCard title="Following" value={String(followed.length)} />
        </div>
      )}

      {followed.length > 0 && (
        <Card style={{ marginBottom: 14 }}>
          <CardHeader title="Your followed pilots" />
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 12 }}>
            {followed.map((p) => (
              <PortfolioCard
                key={p.id}
                portfolio={p}
                onFollow={handleFollow}
                onUnfollow={handleUnfollow}
              />
            ))}
          </div>
        </Card>
      )}

      <Card>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 8 }}>
          <Tabs items={["1W", "1M", "3M", "6M", "1Y"]} active={period} onChange={setPeriod} />
          <Tabs items={["return", "name", "newest"]} active={sort} onChange={setSort} />
        </div>
        {loading ? (
          <EmptyState message="Loading portfolios…" />
        ) : portfolios.length === 0 ? (
          <EmptyState message={error ? "Marketplace offline" : "No pilot portfolios seeded"} />
        ) : (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))",
              gap: 14,
              marginTop: 14,
            }}
          >
            {portfolios.map((p) => (
              <PortfolioCard
                key={p.id}
                portfolio={p}
                onFollow={handleFollow}
                onUnfollow={handleUnfollow}
              />
            ))}
          </div>
        )}
      </Card>

      {dashboard && dashboard.positions.length > 0 && (
        <Card style={{ marginTop: 14 }}>
          <CardHeader title="Mirrored equity positions" />
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Ticker</th>
                  <th>Qty</th>
                  <th>Entry</th>
                  <th>Price</th>
                  <th>P&amp;L</th>
                  <th>Pilot</th>
                </tr>
              </thead>
              <tbody>
                {dashboard.positions.map((pos) => (
                  <tr key={pos.ticker}>
                    <td className="mono">{pos.ticker}</td>
                    <td>{pos.qty}</td>
                    <td>{pos.avg_entry.toFixed(2)}</td>
                    <td>{pos.current_price.toFixed(2)}</td>
                    <td className={cn(pos.unrealized_pl >= 0 ? "kpi-up" : "kpi-down")}>
                      {formatCurrency(pos.unrealized_pl)}
                    </td>
                    <td>{pos.portfolio_id || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </DashboardLayout>
  );
}
