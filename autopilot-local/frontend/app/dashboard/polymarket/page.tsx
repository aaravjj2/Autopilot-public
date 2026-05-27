"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { ApiErrorBanner } from "@/components/terminal/ApiErrorBanner";
import { ApexAreaChart } from "@/components/chart/ApexChart";
import { PageHeader, Card, CardHeader, KpiCard, Tag, Btn, EmptyState } from "@/components/terminal/ui";
import { predictionMarkets, type PolymarketBook } from "@/lib/predictionMarkets";
import { getApexApiUrl } from "@/lib/backend-urls";
import { formatCurrency, cn } from "@/lib/utils";

export default function PolymarketPage() {
  const [book, setBook] = useState<PolymarketBook | null>(null);
  const [source, setSource] = useState<"apex" | "marketplace">("apex");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [runningAgents, setRunningAgents] = useState(false);
  const [agentResult, setAgentResult] = useState<string | null>(null);

  const loadApex = useCallback(async () => {
    const data = await predictionMarkets.getPolymarketBook();
    setBook(data);
    setSource("apex");
  }, []);

  const loadMarketplace = useCallback(async () => {
    const [s, pos, tr, eq] = await Promise.all([
      api.getPolymarketSummary(),
      api.getPolymarketPositions(),
      api.getPolymarketTrades(),
      api.getPolymarketEquityCurve(),
    ]);
    setBook({
      summary: {
        bankroll_usd: s.bankroll_usd,
        open_positions: s.open_positions,
        unrealized_pl: s.unrealized_pl,
        daily_pl: s.daily_pl,
        buying_power_usd: s.bankroll_usd,
      },
      status: { status: "synced", detail: "Copy-trading DB (unified API)" },
      positions: pos.map((p) => ({
        id: p.id,
        market_id: p.market_id,
        question: p.question,
        side: p.side,
        stake_usd: p.stake_usd,
        entry_price: p.entry_price,
        unrealized_pl: p.unrealized_pl,
        opened_at: p.opened_at,
      })),
      trades: tr.map((t) => ({
        id: t.id,
        market_id: t.market_id,
        side: t.side,
        stake_usd: t.stake_usd,
        status: t.status,
        executed_at: t.executed_at,
      })),
      equity_curve: eq.map((p) => ({ date: p.date, bankroll_usd: p.bankroll_usd })),
    });
    setSource("marketplace");
  }, []);

  const load = useCallback(async () => {
    setError(null);
    try {
      await loadApex();
    } catch {
      try {
        await loadMarketplace();
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load Polymarket book");
      }
    } finally {
      setLoading(false);
    }
  }, [loadApex, loadMarketplace]);

  useEffect(() => {
    load();
  }, [load]);

  const handleRunAgents = async () => {
    setRunningAgents(true);
    setAgentResult(null);
    setError(null);
    try {
      const res = (await predictionMarkets.runBothAgents()) as {
        execution_mode?: string;
        polymarket?: { discovery_count?: number; submitted_count?: number; detail?: string };
        kalshi_arb?: {
          scan_count?: number;
          paper_trade_count?: number;
          cached_used?: boolean;
        };
      };
      const poly = res.polymarket;
      const kalshi = res.kalshi_arb;
      setAgentResult(
        `${res.execution_mode ?? "paper_simulated"} · ` +
          `Poly: ${poly?.discovery_count ?? 0} discovered, ${poly?.submitted_count ?? 0} submitted · ` +
          `Kalshi: ${kalshi?.scan_count ?? 0} opps` +
          (kalshi?.cached_used ? " (cached)" : "") +
          `, ${kalshi?.paper_trade_count ?? 0} paper trades`
      );
      await loadApex().catch(() => loadMarketplace());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Agent run failed");
    } finally {
      setRunningAgents(false);
    }
  };

  const handleSync = async () => {
    setSyncing(true);
    try {
      await api.syncPolymarket();
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Sync failed");
    } finally {
      setSyncing(false);
    }
  };

  const curve =
    book?.equity_curve.map((p) => ({
      time: new Date(p.date).getTime(),
      value: p.bankroll_usd,
    })) ?? [];

  return (
    <DashboardLayout>
      <PageHeader
        title="Polymarket Book"
        subtitle="Prediction-market paper book · arb NO legs (not Alpaca copy trading)"
        actions={
          <>
            <span className="pill" style={{ marginRight: 8 }}>
              {source === "apex" ? "APEX audit" : "Marketplace DB"}
            </span>
            <Btn onClick={load} disabled={loading}>
              ↻ Refresh
            </Btn>
            <Btn onClick={handleRunAgents} disabled={runningAgents} style={{ marginLeft: 8 }}>
              {runningAgents ? "Running…" : "Run both agents"}
            </Btn>
            <Btn primary onClick={handleSync} disabled={syncing} style={{ marginLeft: 8 }}>
              {syncing ? "Syncing…" : "Sync copy-trading DB"}
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
        Paper simulation — Polymarket legs are simulated in APEX; not live CLOB orders unless you wire live trading.
      </div>

      {error && (
        <ApiErrorBanner
          message={`Polymarket: ${error}`}
          hint={`APEX / unified API at ${getApexApiUrl()} required.`}
        />
      )}
      {agentResult && (
        <p style={{ marginBottom: 12, fontSize: 13, color: "var(--green)" }}>{agentResult}</p>
      )}

      {loading && !book && <EmptyState message="Loading Polymarket data…" />}

      {book && (
        <>
          <div className="grid grid-kpi" style={{ marginBottom: 14, gridTemplateColumns: "repeat(4, 1fr)" }}>
            <KpiCard title="Bankroll" value={formatCurrency(book.summary.bankroll_usd)} />
            <KpiCard title="Open" value={String(book.summary.open_positions)} />
            <KpiCard
              title="Unrealized"
              value={formatCurrency(book.summary.unrealized_pl)}
              trend={book.summary.unrealized_pl >= 0 ? "up" : "down"}
            />
            <KpiCard title="Feed" value={book.status.status} subValue={book.status.detail} />
          </div>

          <Card style={{ marginBottom: 14 }}>
            <CardHeader
              title="Equity curve"
              action={
                <Link href="/dashboard/arb-radar" className="btn" style={{ fontSize: 12 }}>
                  Arb Radar →
                </Link>
              }
            />
            {curve.length > 0 ? (
              <ApexAreaChart data={curve} height={220} color="#3b82f6" />
            ) : (
              <div className="chart-area" style={{ height: 180 }} />
            )}
          </Card>

          <div className="grid grid-2">
            <Card>
              <CardHeader title="Open positions" />
              {book.positions.length === 0 ? (
                <EmptyState message="No open Polymarket paper positions" />
              ) : (
                <div className="table-wrap" style={{ maxHeight: 400 }}>
                  <table>
                    <thead>
                      <tr>
                        <th>Market</th>
                        <th>Side</th>
                        <th>Stake</th>
                        <th>P&amp;L</th>
                      </tr>
                    </thead>
                    <tbody>
                      {book.positions.map((p) => (
                        <tr key={p.id}>
                          <td>
                            <div style={{ fontSize: 12, maxWidth: 220, overflow: "hidden", textOverflow: "ellipsis" }}>
                              {p.question}
                            </div>
                          </td>
                          <td>
                            <Tag variant={p.side === "YES" ? "long" : "short"}>{p.side}</Tag>
                          </td>
                          <td>{formatCurrency(p.stake_usd)}</td>
                          <td className={cn(p.unrealized_pl >= 0 ? "kpi-up" : "kpi-down")}>
                            {formatCurrency(p.unrealized_pl)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>

            <Card>
              <CardHeader title="Trade history" />
              {book.trades.length === 0 ? (
                <EmptyState message="No trades" />
              ) : (
                <div className="table-wrap" style={{ maxHeight: 400 }}>
                  <table>
                    <thead>
                      <tr>
                        <th>Time</th>
                        <th>Side</th>
                        <th>Stake</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {book.trades.slice(0, 30).map((t) => (
                        <tr key={t.id}>
                          <td style={{ fontSize: 11 }}>
                            {t.executed_at ? new Date(t.executed_at).toLocaleString() : "—"}
                          </td>
                          <td>
                            <Tag variant={t.side === "YES" ? "long" : "short"}>{t.side}</Tag>
                          </td>
                          <td>{formatCurrency(t.stake_usd)}</td>
                          <td>{t.status}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>
          </div>
        </>
      )}
    </DashboardLayout>
  );
}
