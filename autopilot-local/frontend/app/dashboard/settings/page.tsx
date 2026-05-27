"use client";

import { useEffect, useState } from "react";
import { api, HealthData, ApexHealthPayload } from "@/lib/api";
import { getApexApiUrl, getApexDirectUrl } from "@/lib/backend-urls";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { PageHeader, Card, CardHeader, Tag, Btn } from "@/components/terminal/ui";
import { RefreshCw } from "lucide-react";

type IntegrationService = {
  connected: boolean;
  detail?: string;
};

type IntegrationsPayload = Record<string, unknown> & {
  services?: Record<string, IntegrationService>;
};

export default function SettingsPage() {
  const [integrations, setIntegrations] = useState<IntegrationsPayload>({});
  const [apexHealth, setApexHealth] = useState<ApexHealthPayload | null>(null);
  const [marketHealth, setMarketHealth] = useState<HealthData | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [apexDisplayUrl, setApexDisplayUrl] = useState(getApexDirectUrl());

  const loadData = async (force = false) => {
    setError(null);
    try {
      const [intsRes, apexRes, marketRes] = await Promise.allSettled([
        api.getIntegrations(force),
        api.getApexHealth(),
        api.getMarketHealth(),
      ]);
      if (intsRes.status === "fulfilled") setIntegrations(intsRes.value as IntegrationsPayload);
      if (apexRes.status === "fulfilled") setApexHealth(apexRes.value);
      if (marketRes.status === "fulfilled") setMarketHealth(marketRes.value);
      if (intsRes.status === "rejected" && apexRes.status === "rejected" && marketRes.status === "rejected") {
        throw intsRes.reason;
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load settings");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setApexDisplayUrl(getApexApiUrl());
    loadData();
  }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await Promise.all([api.refreshEngine(), api.refreshAll().catch(() => {})]);
      await loadData(true);
    } finally {
      setRefreshing(false);
    }
  };

  const svc = integrations.services ?? {};
  const rows = [
    ["alpaca", "Alpaca", "Broker & market data"],
    ["yfinance", "yfinance", "Market data"],
    ["polymarket", "Polymarket", "Prediction markets"],
    ["tradingagents", "TradingAgents", "AI analysis"],
    ["dexter", "Dexter", "Adversarial research"],
    ["llm", "LLM", "Model provider"],
    ["discord", "Discord", "Signal ingestion"],
  ] as const;

  return (
    <DashboardLayout>
      <PageHeader
        title="Settings & Configuration"
        subtitle="Dual backends · Live integration probes"
        actions={
          <Btn primary onClick={handleRefresh} disabled={refreshing}>
            <RefreshCw size={14} style={{ marginRight: 6 }} />
            {refreshing ? "Refreshing…" : "Refresh"}
          </Btn>
        }
      />

      {error && (
        <Card style={{ marginBottom: 14, color: "var(--red)" }}>{error}</Card>
      )}

      <div className="grid grid-2" style={{ marginBottom: 14 }}>
        <Card>
          <CardHeader title="APEX Engine" />
          <p className="mono" style={{ fontSize: 11, color: "var(--text-dim)", marginBottom: 8 }}>
            {apexDisplayUrl}
          </p>
          <div className="grid grid-2" style={{ gap: 12 }}>
            <div>
              <div style={{ fontSize: 12, color: "var(--text-muted)" }}>Alpaca</div>
              <Tag variant={apexHealth?.alpaca_connected ? "long" : "short"}>
                {apexHealth?.alpaca_connected ? "Connected" : "Disconnected"}
              </Tag>
            </div>
            <div>
              <div style={{ fontSize: 12, color: "var(--text-muted)" }}>Data age</div>
              <div className="mono">{apexHealth?.data_age_seconds ?? "—"}s</div>
            </div>
          </div>
        </Card>
        <Card>
          <CardHeader title="Copy-trading API" />
          <p className="mono" style={{ fontSize: 11, color: "var(--text-dim)", marginBottom: 8 }}>
            {getApexApiUrl()}
          </p>
          <div className="grid grid-2" style={{ gap: 12 }}>
            <div>
              <div style={{ fontSize: 12, color: "var(--text-muted)" }}>Alpaca</div>
              <Tag variant={marketHealth?.alpaca?.status === "connected" ? "long" : "short"}>
                {String(marketHealth?.alpaca?.status ?? "Unknown")}
              </Tag>
            </div>
            <div>
              <div style={{ fontSize: 12, color: "var(--text-muted)" }}>Equity</div>
              <div className="kpi-value" style={{ fontSize: 18 }}>
                {marketHealth?.alpaca?.equity != null
                  ? `$${Number(marketHealth.alpaca.equity).toLocaleString()}`
                  : "N/A"}
              </div>
            </div>
          </div>
        </Card>
      </div>

      <Card style={{ marginBottom: 14 }}>
        <CardHeader title="Integrations (APEX)" action={loading ? <span style={{ fontSize: 11 }}>Loading…</span> : null} />
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Service</th>
                <th>Status</th>
                <th>Detail</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(([key, name, desc]) => {
                const s = svc[key];
                const ok = s?.connected ?? Boolean(integrations[key]);
                return (
                  <tr key={key}>
                    <td>
                      <div style={{ fontWeight: 500 }}>{name}</div>
                      <div style={{ fontSize: 11, color: "var(--text-dim)" }}>{desc}</div>
                    </td>
                    <td>
                      <Tag variant={ok ? "long" : "short"}>{ok ? "Connected" : "Disconnected"}</Tag>
                    </td>
                    <td style={{ fontSize: 11, maxWidth: 280 }} className="mono">
                      {s?.detail ?? "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>

      <div className="grid grid-2">
        <Card>
          <CardHeader title="Risk Configuration" />
          <div className="ticket">
            <label>Max position %</label>
            <input type="number" defaultValue={5} />
            <label>Max open positions</label>
            <input type="number" defaultValue={20} />
            <label>Daily loss limit %</label>
            <input type="number" defaultValue={3} />
            <label>Conviction floor</label>
            <input type="number" defaultValue={6} step={0.5} />
          </div>
        </Card>
        <Card>
          <CardHeader title="Data Configuration" />
          <div className="ticket">
            <label>Watchlist max</label>
            <input type="number" defaultValue={60} />
            <label>Top symbols / day</label>
            <input type="number" defaultValue={5} />
            <label>Earnings blackout days</label>
            <input type="number" defaultValue={2} />
          </div>
        </Card>
      </div>
    </DashboardLayout>
  );
}
