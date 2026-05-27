"use client";

import { useState } from "react";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { PageHeader, Card, CardHeader, Btn, EmptyState } from "@/components/terminal/ui";
import { getApexApiUrl } from "@/lib/backend-urls";

export default function FundAdminPage() {
  const [msg, setMsg] = useState<string | null>(null);

  const downloadTearsheet = async () => {
    setMsg(null);
    try {
      const res = await fetch(`${getApexApiUrl()}/api/fund/tearsheet`);
      if (!res.ok) throw new Error(res.statusText);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "apex-tearsheet.pdf";
      a.click();
      URL.revokeObjectURL(url);
      setMsg("Tearsheet downloaded");
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Download failed");
    }
  };

  return (
    <DashboardLayout>
      <PageHeader
        title="Fund Admin"
        subtitle="Multi-tenant stubs · tear-sheets · copy-scale (Week 10)"
        actions={<Btn primary onClick={downloadTearsheet}>Download PDF</Btn>}
      />
      <Card>
        <CardHeader title="Tenant layer" />
        <EmptyState message="Paper-only fund layer. Configure POSTGRES_URL for multi-tenant mode." />
        {msg && <p style={{ fontSize: 12, marginTop: 12 }}>{msg}</p>}
      </Card>
    </DashboardLayout>
  );
}
