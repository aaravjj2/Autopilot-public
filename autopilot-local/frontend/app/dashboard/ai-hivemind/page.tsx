"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { ApiErrorBanner } from "@/components/terminal/ApiErrorBanner";
import { PageHeader, Card, CardHeader, Btn, EmptyState } from "@/components/terminal/ui";
import { getApexDirectUrl } from "@/lib/backend-urls";

type ArbPick = {
  id?: string;
  kalshi_ticker?: string;
  net_edge?: number;
  settlement_match_score?: number;
  question?: string;
};

export default function AiHivemindPage() {
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [proposal, setProposal] = useState<ArbPick | null>(null);
  const [loading, setLoading] = useState(false);
  const [bootError, setBootError] = useState<string | null>(null);

  const loadProposal = useCallback(async () => {
    setBootError(null);
    try {
      const rows = (await api.listArbOpportunities(10)) as ArbPick[];
      const top = rows.sort((a, b) => (b.net_edge ?? 0) - (a.net_edge ?? 0))[0];
      if (top) {
        setProposal(top);
      } else {
        setProposal({
          kalshi_ticker: "KX-DEMO",
          net_edge: 0.06,
          settlement_match_score: 0.82,
        });
      }
    } catch (e) {
      setBootError(e instanceof Error ? e.message : "Could not load arb proposal");
      setProposal({ kalshi_ticker: "KX-DEMO", net_edge: 0.06, settlement_match_score: 0.82 });
    }
  }, []);

  useEffect(() => {
    loadProposal();
  }, [loadProposal]);

  const runConsensus = async () => {
    if (!proposal) return;
    setLoading(true);
    setResult(null);
    try {
      const out = await api.runAgentsConsensus({
        net_edge: proposal.net_edge ?? 0.05,
        settlement_match_score: proposal.settlement_match_score ?? 0.8,
        kalshi_ticker: proposal.kalshi_ticker ?? "KX-UNKNOWN",
        question: proposal.question,
        arb_id: proposal.id,
      });
      setResult(out);
    } catch (e) {
      setResult({ error: e instanceof Error ? e.message : "consensus failed" });
    } finally {
      setLoading(false);
    }
  };

  return (
    <DashboardLayout>
      <PageHeader
        title="AI Hive-Mind"
        subtitle="Six-agent committee votes on arb proposals (not copy-trading pilots)"
        actions={<Btn onClick={runConsensus}>{loading ? "…" : "Run vote"}</Btn>}
      />

      {bootError && (
        <ApiErrorBanner message={bootError} hint={`Using demo proposal. APEX: ${getApexDirectUrl()}`} />
      )}

      <Card style={{ marginBottom: 14 }}>
        <CardHeader title="Active proposal" />
        {proposal ? (
          <div style={{ padding: "0 14px 14px", fontSize: 13, color: "var(--text-muted)" }}>
            <div className="mono" style={{ color: "var(--text)" }}>
              {proposal.kalshi_ticker ?? "—"}
            </div>
            <div>{proposal.question ?? "Demo / top arb by net edge"}</div>
            <div>
              Edge {(Number(proposal.net_edge ?? 0) * 100).toFixed(2)}% · Settlement{" "}
              {(Number(proposal.settlement_match_score ?? 0) * 100).toFixed(0)}%
            </div>
          </div>
        ) : (
          <EmptyState message="Loading proposal…" />
        )}
      </Card>

      <Card>
        <CardHeader title="Committee log" />
        {!result ? (
          <EmptyState message="Run consensus on the selected arb proposal" />
        ) : (
          <pre
            data-testid="consensus-output"
            style={{ padding: 14, fontSize: 12, overflow: "auto", maxHeight: 480 }}
          >
            {JSON.stringify(result, null, 2)}
          </pre>
        )}
      </Card>
    </DashboardLayout>
  );
}
