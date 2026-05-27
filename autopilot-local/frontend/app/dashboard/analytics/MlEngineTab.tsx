"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { ApiErrorBanner } from "@/components/terminal/ApiErrorBanner";
import { Card, CardHeader, KpiCard, EmptyState } from "@/components/terminal/ui";
import { getApexDirectUrl } from "@/lib/backend-urls";

type MlStatus = {
  self_improvement_enabled?: boolean;
  active_model?: {
    version?: string;
    metrics?: { accuracy?: number; n_samples?: number };
  } | null;
  training_corpus?: { total_rows?: number; labeled_rows?: number };
  backtest_90d?: Record<string, unknown>;
  model_dir?: string;
};

export function MlEngineTab() {
  const [status, setStatus] = useState<MlStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [lastCycle, setLastCycle] = useState<Record<string, unknown> | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setStatus(await api.getMlStatus());
    } catch (e) {
      setError(e instanceof Error ? e.message : "ML status failed");
      setStatus(null);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const runAction = async (label: string, fn: () => Promise<Record<string, unknown>>) => {
    setBusy(label);
    setError(null);
    try {
      const out = await fn();
      if (label === "cycle") setLastCycle(out);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : `${label} failed`);
    } finally {
      setBusy(null);
    }
  };

  const bt = status?.backtest_90d || {};
  const model = status?.active_model;
  const corpus = status?.training_corpus;

  return (
    <>
      {error && <ApiErrorBanner message={error} hint={`APEX ML at ${getApexDirectUrl()}`} />}
      <div className="grid grid-kpi" style={{ margin: "14px 0", gridTemplateColumns: "repeat(4, 1fr)" }}>
        <KpiCard
          title="Active model"
          value={model?.version ? String(model.version).slice(0, 12) : "—"}
        />
        <KpiCard
          title="Model accuracy"
          value={
            model?.metrics?.accuracy != null
              ? `${(Number(model.metrics.accuracy) * 100).toFixed(1)}%`
              : "—"
          }
        />
        <KpiCard title="Labeled rows" value={String(corpus?.labeled_rows ?? "—")} />
        <KpiCard
          title="Arb backtest WR"
          value={
            typeof bt.win_rate === "number"
              ? `${(bt.win_rate * 100).toFixed(0)}%`
              : "—"
          }
        />
      </div>

      <Card>
        <CardHeader
          title="Self-improvement loop"
          subtitle="Export corpus → train logistic edge model → evaluate → promote → refresh brain thresholds"
        />
        {!status && !error && <EmptyState message="Loading ML status…" />}
        {status && (
          <p style={{ fontSize: 13, color: "var(--muted)", margin: "0 0 12px" }}>
            Enabled: {status.self_improvement_enabled ? "yes" : "no"}
            {status.model_dir ? ` · Registry: ${status.model_dir}` : ""}
          </p>
        )}
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <button
            type="button"
            className="btn btn-primary"
            disabled={!!busy}
            onClick={() => runAction("export", () => api.mlExport())}
          >
            {busy === "export" ? "Exporting…" : "Export corpus"}
          </button>
          <button
            type="button"
            className="btn"
            disabled={!!busy}
            onClick={() => runAction("train", () => api.mlTrain())}
          >
            {busy === "train" ? "Training…" : "Train candidate"}
          </button>
          <button
            type="button"
            className="btn"
            disabled={!!busy}
            onClick={() => runAction("evaluate", () => api.mlEvaluate())}
          >
            {busy === "evaluate" ? "Evaluating…" : "Evaluate & promote"}
          </button>
          <button
            type="button"
            className="btn btn-accent"
            disabled={!!busy}
            onClick={() => runAction("cycle", () => api.mlRunCycle())}
          >
            {busy === "cycle" ? "Running cycle…" : "Run full cycle"}
          </button>
        </div>
        {lastCycle && (
          <pre
            style={{
              marginTop: 12,
              fontSize: 11,
              maxHeight: 200,
              overflow: "auto",
              background: "var(--panel)",
              padding: 10,
              borderRadius: 6,
            }}
          >
            {JSON.stringify(lastCycle, null, 2)}
          </pre>
        )}
      </Card>
    </>
  );
}
