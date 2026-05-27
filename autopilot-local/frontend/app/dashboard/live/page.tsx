"use client";

import { useCallback, useEffect, useState } from "react";
import { api, type AuditEvent } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { ApiErrorBanner } from "@/components/terminal/ApiErrorBanner";
import { PageHeader, Card, Tag, EmptyState } from "@/components/terminal/ui";
import { getApexDirectUrl } from "@/lib/backend-urls";

export default function LiveFeedPage() {
  const { events, setEvents, wsConnected } = useAppStore();
  const [filter, setFilter] = useState("");
  const [limit, setLimit] = useState(200);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const preset = (tag: string) => setFilter(tag);

  const load = useCallback(async () => {
    setError(null);
    try {
      const rows = await api.getEvents(limit);
      setEvents(rows);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Events API failed");
    } finally {
      setLoading(false);
    }
  }, [limit, setEvents]);

  useEffect(() => {
    load();
    const t = setInterval(load, 10_000);
    return () => clearInterval(t);
  }, [load]);

  const filtered = events.filter(
    (e: AuditEvent) =>
      !filter ||
      e.event_type.toLowerCase().includes(filter.toLowerCase()) ||
      e.symbol?.toLowerCase().includes(filter.toLowerCase())
  );

  return (
    <DashboardLayout>
      <PageHeader
        title="Live Feed"
        subtitle="APEX audit log · proposals, risk gates, arb fills"
        actions={
          <span className="pill live">
            {filtered.length} events · {wsConnected ? "WS" : "poll"}
          </span>
        }
      />

      {error && (
        <ApiErrorBanner message={error} hint={`Check ${getApexDirectUrl()}/events`} />
      )}

      <Card>
        <div style={{ display: "flex", gap: 8, marginBottom: 12, flexWrap: "wrap" }}>
          {["", "ARB", "GATE", "RISK", "PROPOSAL", "ORDER"].map((p) => (
            <button
              key={p || "all"}
              type="button"
              className="btn"
              style={{ opacity: filter === p ? 1 : 0.6 }}
              onClick={() => preset(p)}
            >
              {p || "All"}
            </button>
          ))}
        </div>
        <div style={{ display: "flex", gap: 12, marginBottom: 12 }}>
          <input
            placeholder="Filter type or symbol…"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            style={{
              flex: 1,
              padding: "8px 12px",
              borderRadius: 6,
              border: "1px solid var(--border)",
              background: "var(--bg-base)",
            }}
          />
          <select className="btn" value={limit} onChange={(e) => setLimit(Number(e.target.value))}>
            <option value={50}>50</option>
            <option value={100}>100</option>
            <option value={200}>200</option>
          </select>
        </div>
        {loading && filtered.length === 0 ? (
          <EmptyState message="Loading audit stream…" />
        ) : filtered.length === 0 ? (
          <EmptyState
            message={
              error
                ? "Could not load events"
                : "No matching events — run Autopilot or paper trades to populate audit_log"
            }
          />
        ) : (
          <div className="table-wrap" style={{ maxHeight: "70vh" }}>
            <table>
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Type</th>
                  <th>Symbol</th>
                  <th>Conv</th>
                  <th>Detail</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((e) => (
                  <tr key={e.id}>
                    <td className="mono">{new Date(e.timestamp).toLocaleTimeString()}</td>
                    <td>
                      <Tag variant="neutral">{e.event_type}</Tag>
                    </td>
                    <td>{e.symbol ?? "—"}</td>
                    <td>{e.conviction?.toFixed(1) ?? "—"}</td>
                    <td style={{ fontSize: 11, color: "var(--text-muted)" }}>
                      {e.rejection_reason || (e.order_id ? `order ${e.order_id}` : "—")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </DashboardLayout>
  );
}
