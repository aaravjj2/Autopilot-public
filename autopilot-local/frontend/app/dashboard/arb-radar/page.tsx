"use client";

import { useEffect, useState } from "react";
import { ThesisCard } from "@/components/ThesisCard";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { PageHeader, Card, CardHeader, Tag, Btn, EmptyState } from "@/components/terminal/ui";
import { cn } from "@/lib/utils";
import { getApexApiUrl, getApexDirectUrl } from "@/lib/backend-urls";
import { useArbStream } from "@/hooks/useArbStream";
import { useArbStore } from "@/lib/useArbStore";

export default function ArbRadarPage() {
  useArbStream("/api/arb/stream");
  const opportunities = useArbStore((s) => s.opportunities);
  const isConnected = useArbStore((s) => s.streamConnected);
  const patchMode = useArbStore((s) => s.patchMode);
  const maxEdge = useArbStore((s) => s.maxEdge);
  const lastPatchAt = useArbStore((s) => s.lastPatchAt);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [demoMode, setDemoMode] = useState(false);
  const loading = !isConnected && opportunities.length === 0;

  useEffect(() => {
    fetch(`${getApexApiUrl()}/api/demo/status`)
      .then((r) => r.json())
      .then((d) => setDemoMode(Boolean(d.demo_mode)))
      .catch(() => setDemoMode(false));
  }, []);

  useEffect(() => {
    if ("Notification" in window && Notification.permission === "default") {
      Notification.requestPermission();
    }
  }, []);

  useEffect(() => {
    const last = opportunities[0];
    if (
      last &&
      last.net_edge >= 0.05 &&
      "Notification" in window &&
      Notification.permission === "granted"
    ) {
      // High-edge alert on stream update (deduped by ticker in session)
      const key = `alert-${last.id}`;
      if (!sessionStorage.getItem(key)) {
        sessionStorage.setItem(key, "1");
        new Notification("High Edge Arb Alert", {
          body: `${last.kalshi_ticker}: ${(last.net_edge * 100).toFixed(1)}% edge`,
        });
      }
    }
  }, [opportunities]);

  const handlePaperTrade = async (id: string) => {
    try {
      const res = await fetch(`${getApexDirectUrl()}/api/arb/${id}/paper-trade`, { method: "POST" });
      const body = await res.json().catch(() => ({}));
      if (res.ok) {
        const k = (body as { kalshi_order_id?: string }).kalshi_order_id;
        const p = (body as { poly_order_id?: string }).poly_order_id;
        alert(`Paper trade OK\nKalshi: ${k}\nPolymarket: ${p}`);
      } else {
        const detail = (body as { detail?: string }).detail || res.statusText;
        alert(`Paper trade rejected: ${detail}`);
      }
    } catch (err) {
      console.error(err);
      alert("Error submitting paper trade — check APEX backend on :8000");
    }
  };

  // Polling UI removed; using connection indicator instead

  return (
    <DashboardLayout>
      <PageHeader
          title="Arb Radar"
          subtitle="Kalshi ↔ Polymarket · live cross-platform spreads"
          actions={
            <>
              <span data-testid="connection-indicator" className="pill" style={{ backgroundColor: isConnected ? "green" : "red", color: "white" }}>
                {isConnected ? "Connected" : "Disconnected"}
              </span>
              <Btn data-testid="reload-button" onClick={() => window.location.reload()}>↻ Reload</Btn>
              <span className="pill" data-testid="patch-mode-indicator">
                {patchMode ? "Patch stream" : "Full sync"}
              </span>
              <span className="pill">
                Max edge <strong style={{ marginLeft: 4 }}>{(maxEdge * 100).toFixed(1)}%</strong>
              </span>
              <span className="pill">
                Pairs <strong style={{ marginLeft: 4 }}>{opportunities.length}</strong>
              </span>
              {lastPatchAt && (
                <span className="pill" data-testid="arb-last-updated">
                  Updated {new Date(lastPatchAt).toLocaleTimeString()}
                </span>
              )}
              {demoMode && <span className="pill">Demo data</span>}
            </>
          }
        />

      <Card>
        <CardHeader title="Opportunities" />
        {loading ? (
          <EmptyState message="Connecting to arb stream…" />
        ) : opportunities.length === 0 ? (
          <EmptyState message="No arbitrage opportunities found" />
        ) : (
          <div className="table-wrap" style={{ maxHeight: "70vh" }}>
            <table>
              <thead>
                <tr>
                  <th>Event</th>
                  <th>Kalshi</th>
                  <th>Poly</th>
                  <th>Volume</th>
                  <th>Gross</th>
                  <th>Net</th>
                  <th>Sizing</th>
                  <th>Match</th>
                  <th>Gates</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {opportunities.map((opp) => (
                  <tr key={opp.id}>
                    <td>
                      <div className="mono" style={{ fontWeight: 600 }}>
                        {opp.kalshi_ticker}
                      </div>
                      <div
                        style={{
                          fontSize: 11,
                          color: "var(--text-muted)",
                          maxWidth: 280,
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                        }}
                        title={opp.question}
                      >
                        {opp.question}
                      </div>
                    </td>
                    <td className="mono">${(Number(opp.kalshi_yes_ask) || 0).toFixed(3)}</td>
                    <td className="mono">${(Number(opp.poly_no_ask) || 0).toFixed(3)}</td>
                    <td style={{ fontSize: 11, color: "var(--text-muted)" }}>
                      K ${(opp.volume_kalshi / 1000).toFixed(1)}k
                      <br />
                      P ${(opp.volume_poly / 1000).toFixed(1)}k
                    </td>
                    <td className="mono kpi-up">
                      $
                      {(
                        Number(opp.gross_spread) ||
                        1 - opp.kalshi_yes_ask - opp.poly_no_ask
                      ).toFixed(3)}
                    </td>
                    <td className="mono kpi-up">{((opp.net_edge || 0) * 100).toFixed(1)}%</td>
                    <td>
                      <span className="pill">{((opp.kelly_fraction || 0) * 100).toFixed(0)}% Kelly</span>
                    </td>
                    <td>
                      <Tag
                        variant={
                          opp.settlement_match_score >= 0.75
                            ? "long"
                            : opp.settlement_match_score >= 0.45
                              ? "neutral"
                              : "short"
                        }
                      >
                        {(opp.settlement_match_score * 100).toFixed(0)}%
                      </Tag>
                    </td>
                    <td>
                      <Tag
                        variant={
                          opp.id === "demo-reject-demo" || (opp.net_edge || 0) < 0.01
                            ? "short"
                            : "long"
                        }
                      >
                        {opp.id === "demo-reject-demo" ? "BLOCK" : "PASS"}
                      </Tag>
                    </td>
                    <td style={{ whiteSpace: "nowrap" }}>
                      <Btn
                        data-testid={`thesis-button-${opp.id}`}
                        onClick={() => setExpandedId(expandedId === opp.id ? null : opp.id)}
                        className={cn(expandedId === opp.id && "btn-primary")}
                      >
                        Thesis
                      </Btn>{" "}
                      <Btn
                        data-testid={`paper-button-${opp.id}`}
                        primary
                        onClick={() => handlePaperTrade(opp.id)}
                      >
                        Paper
                      </Btn>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {expandedId && (
        <Card style={{ marginTop: 14 }}>
          <CardHeader title="Thesis Analysis" />
          <ThesisCard arbId={expandedId} autoStart />
        </Card>
      )}
    </DashboardLayout>
  );
}
