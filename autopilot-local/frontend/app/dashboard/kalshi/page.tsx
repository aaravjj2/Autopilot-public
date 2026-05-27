"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { ApiErrorBanner } from "@/components/terminal/ApiErrorBanner";
import { PageHeader, Card, CardHeader, KpiCard, Tag, Btn, EmptyState } from "@/components/terminal/ui";
import { predictionMarkets, type KalshiBook } from "@/lib/predictionMarkets";
import { formatCurrency, cn } from "@/lib/utils";

export default function KalshiPage() {
  const [book, setBook] = useState<KalshiBook | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [agentsOk, setAgentsOk] = useState<boolean | null>(null);
  const [trading, setTrading] = useState(false);
  const [runningAgents, setRunningAgents] = useState(false);
  const [agentResult, setAgentResult] = useState<string | null>(null);
  const [demoMode, setDemoMode] = useState(false);
  const [kalshiBaseUrl, setKalshiBaseUrl] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const b = await predictionMarkets.getKalshiBook();
      setBook(b);
      setLoading(false);
      void predictionMarkets
        .getAgentsStatus()
        .then((st) => {
          if (st) {
            setAgentsOk(st.kalshi_paper_broker && st.polymarket_paper_broker);
            setDemoMode(Boolean(st.kalshi_demo_trading_enabled && st.kalshi_demo_broker));
            setKalshiBaseUrl(String(st.kalshi_base_url || ""));
          }
        })
        .catch(() => setAgentsOk(false));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load Kalshi book");
      setLoading(false);
    }
  }, []);

  const runBothAgents = async () => {
    setRunningAgents(true);
    setAgentResult(null);
    setError(null);
    try {
      const res = (await predictionMarkets.runBothAgents()) as {
        execution_mode?: string;
        kalshi_arb?: {
          scan_count?: number;
          paper_trade_count?: number;
          cached_used?: boolean;
          duration_sec?: number;
          errors?: string[];
        };
        polymarket?: { submitted_count?: number; discovery_count?: number };
      };
      const k = res.kalshi_arb;
      setAgentResult(
        `Mode: ${res.execution_mode ?? "paper_simulated"} · ` +
          `Kalshi: ${k?.scan_count ?? 0} opps` +
          (k?.cached_used ? " (cached)" : "") +
          `, ${k?.paper_trade_count ?? 0} paper trades` +
          (k?.errors?.length ? ` · ${k.errors.length} skipped` : "") +
          ` · Poly: ${res.polymarket?.submitted_count ?? 0}/${res.polymarket?.discovery_count ?? 0} submitted`
      );
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Agent run failed");
    } finally {
      setRunningAgents(false);
    }
  };

  const placeTopMarketLeg = async () => {
    const top = book?.active_markets?.[0];
    if (!top) return;
    setTrading(true);
    setError(null);
    try {
      await predictionMarkets.placeKalshiPaper({
        ticker: top.kalshi_ticker,
        stake_usd: 50,
        price: 0.5,
        question: top.question,
      });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Paper trade failed");
    } finally {
      setTrading(false);
    }
  };

  useEffect(() => {
    load();
    const t = setInterval(load, 30_000);
    return () => clearInterval(t);
  }, [load]);

  return (
    <DashboardLayout>
      <PageHeader
        title="Kalshi Book"
        subtitle="Event-contract paper positions · cross-venue arb with Polymarket (not copy trading)"
        actions={
          <>
            <span className="pill" style={{ marginRight: 8 }}>
              {agentsOk === null ? "Agents…" : agentsOk ? "Agents ready" : "Brokers off"}
            </span>
            <Btn onClick={runBothAgents} disabled={runningAgents}>
              {runningAgents ? "…" : "Run both agents"}
            </Btn>
            <Btn
              onClick={placeTopMarketLeg}
              disabled={trading || !book?.active_markets?.length}
              style={{ marginLeft: 8 }}
            >
              {trading ? "…" : "Paper top"}
            </Btn>
            <Btn onClick={load} disabled={loading} style={{ marginLeft: 8 }}>
              {loading ? "…" : "↻ Refresh"}
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
        {demoMode
          ? `Kalshi demo API — orders are sent to ${kalshiBaseUrl || "demo-api.kalshi.co"} and appear on your Kalshi demo account.`
          : "Internal paper only — enable KALSHI_DEMO_TRADING_ENABLED in .env to post orders to the Kalshi demo API."}
      </div>

      {error && (
        <ApiErrorBanner
          message={`Kalshi API: ${error}`}
          hint="Start APEX on :8000. Arb pairs live on Arb Radar."
        />
      )}
      {agentResult && (
        <p style={{ marginBottom: 12, fontSize: 13, color: "var(--green)" }}>{agentResult}</p>
      )}

      {book && (
        <p style={{ marginBottom: 12, fontSize: 12, color: "var(--muted)" }}>
          {book.execution_mode === "paper_simulated"
            ? "Paper book"
            : book.execution_mode || "paper"}{" "}
          · {book.trades.length} fills in APEX audit · not visible on kalshi.com
        </p>
      )}

      {loading && !book && <EmptyState message="Loading Kalshi book…" />}

      {book && (
        <>
          <div className="grid grid-kpi" style={{ marginBottom: 14, gridTemplateColumns: "repeat(4, 1fr)" }}>
            <KpiCard title="Bankroll" value={formatCurrency(book.bankroll_usd)} />
            <KpiCard title="Buying power" value={formatCurrency(book.buying_power_usd)} />
            <KpiCard title="Open legs" value={String(book.open_positions)} />
            <KpiCard
              title="Feed"
              value={book.status.status}
              subValue={book.status.detail}
            />
          </div>

          <Card style={{ marginBottom: 14 }}>
            <CardHeader
              title="Active arb markets (Kalshi leg)"
              action={
                <Link href="/dashboard/arb-radar" className="btn" style={{ fontSize: 12 }}>
                  Open Arb Radar →
                </Link>
              }
            />
            {book.active_markets.length === 0 ? (
              <EmptyState message="No cached arb pairs — run scan from Arb Radar" />
            ) : (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Ticker</th>
                      <th>Question</th>
                      <th>Net edge</th>
                    </tr>
                  </thead>
                  <tbody>
                    {book.active_markets.map((m) => (
                      <tr key={m.id}>
                        <td className="mono">{m.kalshi_ticker}</td>
                        <td style={{ maxWidth: 320, overflow: "hidden", textOverflow: "ellipsis" }}>
                          {m.question}
                        </td>
                        <td className="kpi-up">{(m.net_edge * 100).toFixed(2)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>

          <div className="grid grid-2">
            <Card>
              <CardHeader title="Paper positions" />
              {book.positions.length === 0 ? (
                <EmptyState message="No Kalshi paper fills in audit log yet" />
              ) : (
                <div className="table-wrap" style={{ maxHeight: 400 }}>
                  <table>
                    <thead>
                      <tr>
                        <th>Ticker</th>
                        <th>Stake</th>
                        <th>Entry</th>
                      </tr>
                    </thead>
                    <tbody>
                      {book.positions.map((p) => (
                        <tr key={p.id}>
                          <td className="mono">{p.ticker}</td>
                          <td>{formatCurrency(p.stake_usd)}</td>
                          <td className="mono">${p.entry_price.toFixed(3)}</td>
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
                <EmptyState message="No Kalshi trades" />
              ) : (
                <div className="table-wrap" style={{ maxHeight: 400 }}>
                  <table>
                    <thead>
                      <tr>
                        <th>Time</th>
                        <th>Ticker</th>
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
                          <td className="mono">{t.ticker}</td>
                          <td>{formatCurrency(t.stake_usd)}</td>
                          <td>
                            <Tag variant="long">{t.status}</Tag>
                          </td>
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
