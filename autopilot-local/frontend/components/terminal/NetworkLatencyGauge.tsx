"use client";

import { useEffect, useState } from "react";
import { getApexApiUrl, getApexWsUrl } from "@/lib/backend-urls";

type LatencyState = {
  apiMs: number | null;
  wsMs: number | null;
  arbMs: number | null;
};

export function NetworkLatencyGauge() {
  const [lat, setLat] = useState<LatencyState>({ apiMs: null, wsMs: null, arbMs: null });

  useEffect(() => {
    let cancelled = false;

    const pingApi = async () => {
      const t0 = performance.now();
      try {
        const r = await fetch(`${getApexApiUrl()}/health`);
        if (r.ok && !cancelled) {
          setLat((s) => ({ ...s, apiMs: Math.round(performance.now() - t0) }));
        }
      } catch {
        if (!cancelled) setLat((s) => ({ ...s, apiMs: null }));
      }
    };

    const pingWs = () =>
      new Promise<void>((resolve) => {
        const t0 = performance.now();
        const ws = new WebSocket(getApexWsUrl("/ws"));
        const done = () => {
          ws.close();
          resolve();
        };
        ws.onopen = () => {
          if (!cancelled) {
            setLat((s) => ({ ...s, wsMs: Math.round(performance.now() - t0) }));
          }
          done();
        };
        ws.onerror = done;
        setTimeout(done, 5000);
      });

    const pingArb = () =>
      new Promise<void>((resolve) => {
        const t0 = performance.now();
        const ws = new WebSocket(getApexWsUrl("/api/arb/stream"));
        const done = () => {
          ws.close();
          resolve();
        };
        ws.onmessage = () => {
          if (!cancelled) {
            setLat((s) => ({ ...s, arbMs: Math.round(performance.now() - t0) }));
          }
          done();
        };
        ws.onerror = done;
        setTimeout(done, 8000);
      });

    const run = async () => {
      await pingApi();
      await pingWs();
      await pingArb();
    };
    run();
    const id = setInterval(run, 20000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  const fmt = (ms: number | null) => (ms == null ? "—" : `${ms}ms`);

  return (
    <div className="latency-gauge" data-testid="latency-gauge" style={{ fontSize: 10, color: "var(--text-dim)" }}>
      <span>API {fmt(lat.apiMs)}</span>
      <span style={{ marginLeft: 8 }}>WS {fmt(lat.wsMs)}</span>
      <span style={{ marginLeft: 8 }}>Arb {fmt(lat.arbMs)}</span>
    </div>
  );
}
