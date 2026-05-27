"use client";

import { useEffect, useState } from "react";
import { getApexApiUrl } from "@/lib/backend-urls";

export function DemoBanner() {
  const [demo, setDemo] = useState(false);

  useEffect(() => {
    if (process.env.NEXT_PUBLIC_DEMO_MODE === "true") {
      setDemo(true);
      return;
    }
    fetch(`${getApexApiUrl()}/api/demo/status`)
      .then((r) => r.json())
      .then((d) => setDemo(Boolean(d.demo_mode)))
      .catch(() => setDemo(false));
  }, []);

  if (!demo) return null;

  return (
    <div
      role="status"
      data-testid="demo-banner"
      style={{
        background: "linear-gradient(90deg, #1a3a5c, #0d2137)",
        color: "#9ec9ff",
        padding: "8px 16px",
        fontSize: 13,
        textAlign: "center",
        borderBottom: "1px solid var(--border)",
      }}
    >
      Demo data · Paper trading only · No live venue keys required
    </div>
  );
}
