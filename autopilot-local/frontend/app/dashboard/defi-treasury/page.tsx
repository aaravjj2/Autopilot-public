"use client";

import { useEffect, useState } from "react";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { PageHeader, Card, CardHeader, KpiCard, Tag, EmptyState } from "@/components/terminal/ui";
import { getApexApiUrl } from "@/lib/backend-urls";
import { formatCurrency } from "@/lib/utils";

type TreasuryStatus = {
  aave?: { status: string; apy_pct?: number };
  sweep?: { last_sweep_usd?: number; status: string };
  mev?: { sandwich_detected?: boolean; status: string };
  oneinch?: { route_available?: boolean };
};

export default function DefiTreasuryPage() {
  const [data, setData] = useState<TreasuryStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${getApexApiUrl()}/api/defi/treasury`)
      .then((r) => r.json())
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, []);

  return (
    <DashboardLayout>
      <PageHeader title="DeFi Treasury" subtitle="Aave sweep · 1inch routing · MEV guard (paper)" />
      {loading ? (
        <EmptyState message="Loading treasury status…" />
      ) : !data ? (
        <EmptyState message="Treasury API unavailable" />
      ) : (
        <div className="grid grid-kpi" style={{ gridTemplateColumns: "repeat(4, 1fr)" }}>
          <KpiCard title="Aave" value={data.aave?.status || "—"} subValue={`${data.aave?.apy_pct ?? 0}% APY`} />
          <KpiCard
            title="Last sweep"
            value={formatCurrency(data.sweep?.last_sweep_usd ?? 0)}
            subValue={data.sweep?.status || "idle"}
          />
          <KpiCard title="MEV" value={data.mev?.status || "—"} subValue={data.mev?.sandwich_detected ? "Alert" : "Clear"} />
          <Card>
            <CardHeader title="1inch" />
            <Tag variant={data.oneinch?.route_available ? "long" : "neutral"}>
              {data.oneinch?.route_available ? "Routes OK" : "Stub"}
            </Tag>
          </Card>
        </div>
      )}
    </DashboardLayout>
  );
}
