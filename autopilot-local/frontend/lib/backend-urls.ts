/**
 * APEX trading engine (backend_api.py).
 * HTTP: browser uses same-origin /apex-api (Next rewrite → :8000).
 * WebSocket: direct engine URL — Next rewrites do not upgrade WS.
 */

const DEFAULT_APEX_HTTP = "http://127.0.0.1:8000";

/** Direct engine URL (env). Use for WebSockets and long-running POSTs. */
export function getApexDirectUrl(): string {
  return (
    process.env.NEXT_PUBLIC_APEX_API_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    DEFAULT_APEX_HTTP
  );
}

/** Runtime HTTP base for fetches (browser → /apex-api proxy when configured). */
export function getApexApiUrl(): string {
  if (typeof window !== "undefined") {
    return (
      process.env.NEXT_PUBLIC_APEX_API_BROWSER_URL ||
      process.env.NEXT_PUBLIC_APEX_API_PROXY ||
      "/apex-api"
    );
  }
  return getApexDirectUrl();
}

/** WebSocket URL on the engine (not through Next dev proxy). */
export function getApexWsUrl(path: string): string {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  const wsOverride = process.env.NEXT_PUBLIC_APEX_WS_URL;
  if (wsOverride) {
    return `${wsOverride.replace(/\/$/, "")}${normalized}`;
  }
  const http = getApexDirectUrl();
  const ws = http.replace(/^https:\/\//, "wss://").replace(/^http:\/\//, "ws://");
  return `${ws.replace(/\/$/, "")}${normalized}`;
}

/** @deprecated Use getApexApiUrl() for HTTP or getApexWsUrl() for WS */
export const apexWsUrl = getApexWsUrl;

/** SSR-safe default for static copy (prefer getApexApiUrl() after mount). */
export const APEX_API_URL = getApexDirectUrl();

/** Copy-trading marketplace routes — same unified backend as APEX (:8000). */
export function getMarketplaceApiUrl(): string {
  return getApexApiUrl();
}

/** @deprecated Use getMarketplaceApiUrl() */
export const MARKETPLACE_API_URL = getApexDirectUrl();

/** @deprecated Use getApexWsUrl() — marketplace WS is on :8000 */
export const marketWsUrl = (path: string) => getApexWsUrl(path);
