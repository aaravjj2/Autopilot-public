"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { ApexAreaChart } from "@/components/chart/ApexChart";
import {
  PageHeader,
  KpiCard,
  Card,
  CardHeader,
  Tag,
  StatusBadge,
  Pipeline,
  Btn,
  EmptyState,
} from "@/components/terminal/ui";
import { formatCurrency, formatPercent, cn, getChangeColor } from "@/lib/utils";
import { AlertCircle, CheckCircle, AlertTriangle } from "lucide-react";

export default function DashboardPage() {
  const {
    account,
    setAccount,
    positions,
    setPositions,
    opportunities,
    setOpportunities,
    events,
    setEvents,
    wsConnected,
    wsLastUpdate,
    wsDataStale,
  } = useAppStore();

  const [equityCurve, setEquityCurve] = useState<Array<{ time: number; value: number }>>([]);
  const [pmBrain, setPmBrain] = useState<Awaited<ReturnType<typeof api.getPmBrain>> | null>(null);
  const [arbSummary, setArbSummary] = useState<{
    active_opportunities: number;
    win_rate: number;
  } | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    async function loadData() {
      try {
        const [snap, history, arb, brain] = await Promise.allSettled([
          api.getDashboardSnapshot(),
          api.getAccountHistory(30),
          api.getArbSummary(),
          api.getPmBrain(),
        ]);

        if (snap.status === "fulfilled") {
          const s = snap.value;
          if (s.account) setAccount(s.account);
          setPositions(s.positions || []);
          setOpportunities(s.opportunities || []);
          if (s.events?.length) setEvents(s.events);
        }
        if (arb.status === "fulfilled") setArbSummary(arb.value);
        if (brain.status === "fulfilled") setPmBrain(brain.value);

        const accountSnapshot =
          snap.status === "fulfilled" ? snap.value.account : account;
        if (history.status === "fulfilled" && Array.isArray(history.value) && history.value.length > 0) {
          setEquityCurve(
            history.value.map((h: { time?: number; equity?: number; portfolio_value?: number }) => ({
              time: h.time || Date.now(),
              value: h.equity || h.portfolio_value || 0,
            }))
          );
        } else if (accountSnapshot?.equity) {
          setEquityCurve([{ time: Date.now(), value: accountSnapshot.equity }]);
        }
      } catch (error) {
        console.error("Failed to load dashboard data:", error);
      }
    }

    loadData();
    const interval = setInterval(loadData, wsConnected ? 60000 : 15000);
    return () => clearInterval(interval);
  }, [account, wsConnected, setAccount, setPositions, setOpportunities, setEvents]);

  const topOpportunities = opportunities.slice(0, 5);
  const recentEvents = events.slice(0, 8);
  const unrealized = positions.reduce((s, p) => s + p.unrealized_pl, 0);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await api.refreshEngine();
    } finally {
      setRefreshing(false);
    }
  };

  return (
    <DashboardLayout showRightPanel defaultSymbol={positions[0]?.symbol}>
      {wsDataStale && (
        <div className="card" style={{ marginBottom: 14, borderColor: "rgba(245,158,11,0.4)", color: "var(--amber)" }}>
          <AlertCircle size={16} style={{ display: "inline", marginRight: 8 }} />
          Data may be stale — last update over 5 minutes ago.
        </div>
      )}

      <PageHeader
        title="Command Center"
        subtitle={
          <>
            Real-time portfolio · Engine RUNNING ·{" "}
            <span className="mono" suppressHydrationWarning>
              {mounted && wsLastUpdate
                ? new Date(wsLastUpdate).toLocaleTimeString()
                : "syncing…"}
            </span>
          </>
        }
        actions={
          <>
            <Btn onClick={handleRefresh} disabled={refreshing}>
              {refreshing ? "Refreshing…" : "Refresh Cache"}
            </Btn>
            <StatusBadge status={wsConnected ? "LIVE" : "POLLING"} />
          </>
        }
      />

      <div className="grid grid-kpi" style={{ marginBottom: 14 }}>
        <KpiCard
          title="Portfolio"
          value={formatCurrency(account?.equity || 0)}
          subValue={`${(account?.daily_pl_pct ?? 0).toFixed(2)}% today`}
          trend={(account?.daily_pl ?? 0) >= 0 ? "up" : "down"}
        />
        <KpiCard title="Buying Power" value={formatCurrency(account?.buying_power || 0)} subValue={`Cash ${formatCurrency(account?.cash || 0)}`} />
        <KpiCard
          title="Positions"
          value={String(positions.length)}
          subValue={`${positions.filter((p) => p.unrealized_pl > 0).length} profitable`}
        />
        <KpiCard
          title="Signals"
          value={String(opportunities.length)}
          subValue={`${opportunities.filter((o) => o.conviction >= 7).length} high conviction`}
        />
        <KpiCard
          title="Arb Active"
          value={String(arbSummary?.active_opportunities ?? 0)}
          subValue={arbSummary ? `${formatPercent(arbSummary.win_rate)} win rate` : "—"}
          trend={(arbSummary?.win_rate ?? 0) >= 0.5 ? "up" : "down"}
        />
      </div>

      <Card className="" style={{ marginBottom: 14 }}>
        <CardHeader title="Real-time P&L" />
        <div className="grid grid-2" style={{ gridTemplateColumns: "repeat(4, 1fr)" }}>
          <div>
            <div style={{ fontSize: 12, color: "var(--text-muted)" }}>Unrealized</div>
            <div className={cn("kpi-value", getChangeColor(unrealized))}>{formatCurrency(unrealized)}</div>
          </div>
          <div>
            <div style={{ fontSize: 12, color: "var(--text-muted)" }}>Daily P&L</div>
            <div className={cn("kpi-value", getChangeColor(account?.daily_pl ?? 0))}>
              {formatCurrency(account?.daily_pl ?? 0)}
            </div>
          </div>
          <div>
            <div style={{ fontSize: 12, color: "var(--text-muted)" }}>Position value</div>
            <div className="kpi-value">{formatCurrency(positions.reduce((s, p) => s + p.market_value, 0))}</div>
          </div>
          <div>
            <div style={{ fontSize: 12, color: "var(--text-muted)" }}>Cash</div>
            <div className="kpi-value">{formatCurrency(account?.cash || 0)}</div>
          </div>
        </div>
      </Card>

      {pmBrain && (
        <Card style={{ marginBottom: 14 }}>
          <CardHeader
            title="Prediction Market Brain"
            action={
              <Link href="/dashboard/arb-radar" className="btn btn-ghost" style={{ fontSize: 12 }}>
                Arb Radar →
              </Link>
            }
          />
          <p style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 10 }}>{pmBrain.guidance}</p>
          <div className="grid grid-3" style={{ marginBottom: 10 }}>
            <div>
              <div style={{ fontSize: 11, color: "var(--text-dim)" }}>Kalshi</div>
              <Tag variant={pmBrain.kalshi.status === "ok" ? "long" : "neutral"}>{pmBrain.kalshi.status}</Tag>
              <div style={{ fontSize: 11, marginTop: 4 }}>{pmBrain.kalshi.detail || "—"}</div>
            </div>
            <div>
              <div style={{ fontSize: 11, color: "var(--text-dim)" }}>Polymarket</div>
              <Tag variant={pmBrain.polymarket.status === "ok" ? "long" : "neutral"}>
                {pmBrain.polymarket.status}
              </Tag>
              <div style={{ fontSize: 11, marginTop: 4 }}>{pmBrain.polymarket.detail || "—"}</div>
            </div>
            <div>
              <div style={{ fontSize: 11, color: "var(--text-dim)" }}>Arb cache</div>
              <div className="mono" style={{ fontSize: 13 }}>
                {pmBrain.arb.cached_opportunities} pairs · top {(pmBrain.arb.top_net_edge * 100).toFixed(1)}%
              </div>
            </div>
          </div>
          {pmBrain.recent_opportunities.length > 0 && (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Ticker</th>
                    <th>Edge</th>
                    <th>Settle</th>
                  </tr>
                </thead>
                <tbody>
                  {pmBrain.recent_opportunities.slice(0, 5).map((o) => (
                    <tr key={o.id}>
                      <td className="mono">{o.kalshi_ticker}</td>
                      <td className="kpi-up">{(o.net_edge * 100).toFixed(1)}%</td>
                      <td>{(o.settlement_match_score * 100).toFixed(0)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}

      <div className="grid grid-3" style={{ marginBottom: 14 }}>
        <Card>
          <CardHeader title="Equity Curve · 30D" />
          {equityCurve.length > 0 ? (
            <ApexAreaChart data={equityCurve} height={220} />
          ) : (
            <div className="chart-area" />
          )}
        </Card>
        <Card>
          <CardHeader title="Risk snapshot" />
          <div className="gauge-row">
            <div className="gauge">
              <div className="gauge-ring">{((account?.daily_pl_pct ?? 0) / 100).toFixed(1)}%</div>
              <span style={{ fontSize: 11, color: "var(--text-dim)" }}>Daily</span>
            </div>
            <div className="gauge">
              <div className="gauge-ring" style={{ borderTopColor: "var(--amber)" }}>
                {positions.length}
              </div>
              <span style={{ fontSize: 11, color: "var(--text-dim)" }}>Open</span>
            </div>
          </div>
        </Card>
      </div>

      <div className="grid grid-2" style={{ marginBottom: 14 }}>
        <Card>
          <CardHeader title="Watchlist" action={<Btn className="btn-ghost">+ Add</Btn>} />
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Side</th>
                  <th>P&amp;L</th>
                  <th>Conv</th>
                </tr>
              </thead>
              <tbody>
                {positions.slice(0, 6).map((p) => (
                  <tr key={p.symbol}>
                    <td className="mono" style={{ fontWeight: 600 }}>
                      {p.symbol}
                    </td>
                    <td>
                      <Tag variant={p.side === "long" ? "long" : "short"}>{p.side}</Tag>
                    </td>
                    <td className={cn(p.unrealized_pl >= 0 ? "kpi-up" : "kpi-down")}>
                      {formatCurrency(p.unrealized_pl)}
                    </td>
                    <td>—</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
        <Card>
          <CardHeader title="Agent Pipeline" />
          <Pipeline
            stages={[
              { id: "l0", label: "L0", sub: "Ingest", active: true },
              { id: "l1", label: "L1", sub: "Brain", active: true },
              { id: "l2", label: "L2", sub: "Agents", active: true },
              { id: "l3", label: "L3", sub: "Exec" },
              { id: "l4", label: "L4", sub: "Obs" },
            ]}
          />
        </Card>
      </div>

      <div className="grid grid-2">
        <Card>
          <CardHeader title="Top Signals" action={<Link href="/dashboard/opportunities" className="btn btn-ghost">View all</Link>} />
          {topOpportunities.length === 0 ? (
            <EmptyState message="No opportunities yet" />
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Symbol</th>
                    <th>Dir</th>
                    <th>Conv</th>
                    <th>PM</th>
                  </tr>
                </thead>
                <tbody>
                  {topOpportunities.map((o) => (
                    <tr key={o.symbol}>
                      <td>{o.symbol}</td>
                      <td>
                        <Tag variant={o.direction === "LONG" ? "long" : "short"}>{o.direction}</Tag>
                      </td>
                      <td>{o.conviction.toFixed(1)}</td>
                      <td>{o.pm_signal}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
        <Card>
          <CardHeader title="Recent Activity" />
          {recentEvents.length === 0 ? (
            <EmptyState message="No events yet" />
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {recentEvents.map((e) => (
                <div
                  key={e.id}
                  style={{
                    display: "flex",
                    gap: 10,
                    padding: 10,
                    borderRadius: 6,
                    background: "var(--bg-elevated)",
                  }}
                >
                  {e.rejection_reason ? (
                    <AlertTriangle size={14} color="var(--red)" />
                  ) : (
                    <CheckCircle size={14} color="var(--green)" />
                  )}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 13, fontWeight: 500 }}>
                      {e.event_type}
                      {e.symbol ? ` · ${e.symbol}` : ""}
                    </div>
                    {e.rejection_reason && (
                      <div style={{ fontSize: 11, color: "var(--red)" }}>{e.rejection_reason}</div>
                    )}
                  </div>
                  <span className="mono" style={{ fontSize: 11, color: "var(--text-dim)" }}>
                    {new Date(e.timestamp).toLocaleTimeString()}
                  </span>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </DashboardLayout>
  );
}
