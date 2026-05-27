"use client";

import { useEffect } from "react";
import { useArbStore } from "@/lib/useArbStore";
import { getApexApiUrl, getApexWsUrl } from "@/lib/backend-urls";
import { normalizeArbRows } from "@/lib/arbNormalize";

/** WebSocket hook for /api/arb/stream with REST bootstrap and reconnect backoff. */
export function useArbStream(path = "/api/arb/stream") {
  const handleStreamMessage = useArbStore((s) => s.handleStreamMessage);
  const applySync = useArbStore((s) => s.applySync);
  const setConnected = useArbStore((s) => s.setConnected);

  useEffect(() => {
    let ws: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let closed = false;
    let attempt = 0;

    const bootstrap = async () => {
      try {
        const res = await fetch(`${getApexApiUrl()}/api/arb/opportunities?limit=200`, {
          cache: "no-store",
        });
        if (res.ok) {
          const rows = await res.json();
          applySync(normalizeArbRows(rows));
        }
      } catch (err) {
        console.warn("arb REST bootstrap failed", err);
      }
    };

    void bootstrap();

    const connect = () => {
      ws = new WebSocket(getApexWsUrl(path));
      ws.onopen = () => {
        attempt = 0;
        setConnected(true);
      };
      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data as string) as Record<string, unknown>;
          handleStreamMessage(msg);
        } catch (err) {
          console.error("arb stream parse error", err);
        }
      };
      ws.onerror = () => ws?.close();
      ws.onclose = () => {
        setConnected(false);
        if (!closed) {
          attempt += 1;
          const delay = Math.min(30_000, 1000 * 2 ** Math.min(attempt, 5));
          reconnectTimer = setTimeout(connect, delay);
        }
      };
    };

    connect();

    return () => {
      closed = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      ws?.close();
      setConnected(false);
    };
  }, [path, handleStreamMessage, applySync, setConnected]);
}
