import type { BacktestResult } from "@/types/arb";
import { getApexApiUrl, getApexDirectUrl, getMarketplaceApiUrl } from "@/lib/backend-urls";

export { getApexApiUrl, getApexDirectUrl, getMarketplaceApiUrl };

async function fetchBase<T>(base: string, endpoint: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${base}${endpoint}`, {
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    throw new Error(`API Error: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

const fetchApex = <T>(endpoint: string, options?: RequestInit) =>
  fetchBase<T>(getApexApiUrl(), endpoint, options);

const fetchMarket = <T>(endpoint: string, options?: RequestInit) =>
  fetchBase<T>(getMarketplaceApiUrl(), endpoint, options);

// ============================================================================
// Unified backend (APEX + copy-trading marketplace on :8000)
// ============================================================================

export interface PortfolioCard {
  id: string;
  name: string;
  description?: string;
  category: string;
  pilot_name: string;
  is_following: boolean;
  return_pct: number;
  aum_usd: number;
  holdings_count: number;
  last_refreshed_at: string | null;
  holdings?: {
    ticker: string;
    weight: number;
    weight_pct: number;
    shares: number;
    price: number;
    value_usd: number;
  }[];
  trades?: {
    id: string;
    ticker: string;
    side: string;
    qty: number;
    price: number;
    status: string;
    executed_at: string | null;
  }[];
  performance?: { date: string; value: number; return_pct: number }[];
  benchmark_return_pct?: number;
  sharpe_ratio?: number;
  spec?: Record<string, unknown>;
}

export interface DashboardData {
  account: {
    equity: number;
    cash: number;
    buying_power: number;
    unrealized_pl: number;
  };
  followed_portfolios: PortfolioCard[];
  positions: {
    ticker: string;
    qty: number;
    avg_entry: number;
    current_price: number;
    unrealized_pl: number;
    portfolio_id: string;
  }[];
  trades: {
    portfolio_id: string;
    ticker: string;
    side: string;
    qty: number;
    price: number;
    status: string;
    executed_at: string | null;
  }[];
}

export interface HealthData {
  alpaca: Record<string, unknown>;
  last_refresh: Record<string, string>;
  timestamp: string;
  engine?: Record<string, unknown>;
}

// ============================================================================
// APEX Engine Types (backend_api.py :8000)
// ============================================================================

export interface Position {
  symbol: string;
  qty: number;
  market_value: number;
  avg_entry_price: number;
  current_price: number;
  side: "long" | "short";
  unrealized_pl: number;
  unrealized_plpc: number;
  sector: string;
}

export interface AccountSnapshot {
  equity: number;
  buying_power: number;
  cash: number;
  portfolio_value: number;
  daily_pl: number;
  daily_pl_pct: number;
}

export interface TradeProposal {
  id: string;
  symbol: string;
  direction: "LONG" | "SHORT";
  instrument: string;
  entry_price: number;
  stop_loss: number;
  take_profit: number;
  conviction: number;
  status: string;
  created_at: string;
}

export interface AuditEvent {
  id: string;
  event_type: string;
  symbol?: string;
  conviction?: number;
  rejection_reason?: string;
  order_id?: string;
  timestamp: string;
  raw_payload: Record<string, unknown>;
}

export interface OpportunityScore {
  symbol: string;
  direction: string;
  instrument: string;
  conviction: number;
  technical_score: number;
  fundamental_score: number;
  pm_signal: string;
  catalyst: string;
  risk_reward: number;
}

export interface ChartBar {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
}

export interface OptionChain {
  symbol: string;
  expiry: string;
  calls: OptionContract[];
  puts: OptionContract[];
}

export interface OptionContract {
  strike: number;
  bid: number;
  ask: number;
  last: number;
  change: number;
  volume: number;
  open_interest: number;
  implied_volatility: number;
  delta: number;
  gamma: number;
  theta: number;
  vega: number;
}

export interface PolymarketSummary {
  bankroll_usd: number;
  buying_power_usd: number;
  total_staked: number;
  total_value: number;
  unrealized_pl: number;
  open_positions: number;
  daily_pl: number;
  daily_pl_pct: number;
}

export interface PolymarketPosition {
  id: number;
  market_id: string;
  question: string;
  slug: string;
  side: "YES" | "NO";
  entry_price: number;
  stake_usd: number;
  quantity: number;
  current_value: number;
  unrealized_pl: number;
  status: "open" | "resolved_yes" | "resolved_no" | "closed";
  opened_at: string | null;
  resolved_at: string | null;
}

export interface PolymarketTrade {
  id: number;
  market_id: string;
  question: string;
  side: "YES" | "NO";
  stake_usd: number;
  entry_price: number;
  exit_price: number | null;
  order_id: string;
  status: "filled" | "cancelled" | "failed";
  executed_at: string | null;
}

export interface PolymarketEquityPoint {
  date: string;
  bankroll_usd: number;
  buying_power_usd: number;
  daily_pl: number;
  daily_pl_pct: number;
}

export interface ApexHealthPayload {
  status: string;
  alpaca_connected: boolean;
  data_age_seconds: number;
  last_cache_update: string | null;
  timestamp: string;
}

// ============================================================================
// Unified API — routes to correct backend
// ============================================================================

export const api = {
  // --- Copy-trading marketplace (same origin as APEX) ---

  getDashboard: () => fetchMarket<DashboardData>("/api/dashboard"),

  listPortfolios: (params?: { period?: string; category?: string; sort?: string }) => {
    const qs = new URLSearchParams();
    if (params?.period) qs.set("period", params.period);
    if (params?.category) qs.set("category", params.category);
    if (params?.sort) qs.set("sort", params.sort);
    const q = qs.toString();
    return fetchMarket<PortfolioCard[]>(`/api/portfolios${q ? `?${q}` : ""}`);
  },

  getPortfolio: (id: string, period: string = "1M") =>
    fetchMarket<PortfolioCard>(`/api/portfolios/${id}?period=${period}`),

  followPortfolio: (id: string) =>
    fetchMarket<Record<string, unknown>>(`/api/portfolios/${id}/follow`, { method: "POST" }),

  unfollowPortfolio: (id: string) =>
    fetchMarket<Record<string, unknown>>(`/api/portfolios/${id}/follow`, { method: "DELETE" }),

  getMarketHealth: () => fetchMarket<HealthData>("/api/health"),

  refreshAll: () => fetchMarket<Record<string, unknown>>("/api/refresh/all", { method: "POST" }),

  refreshPortfolio: (id: string) =>
    fetchMarket<Record<string, unknown>>(`/api/refresh/${id}`, { method: "POST" }),

  getPolymarketSummary: () => fetchMarket<PolymarketSummary>("/api/polymarket/summary"),

  getPolymarketPositions: () => fetchMarket<PolymarketPosition[]>("/api/polymarket/positions"),

  getPolymarketTrades: () => fetchMarket<PolymarketTrade[]>("/api/polymarket/trades"),

  getPolymarketEquityCurve: () =>
    fetchMarket<PolymarketEquityPoint[]>("/api/polymarket/equity-curve"),

  syncPolymarket: () =>
    fetchMarket<Record<string, unknown>>("/api/polymarket/sync", { method: "POST" }),

  /** Marketplace Alpaca positions (copy-trading tagged) */
  getMarketPositions: () => fetchMarket<Record<string, unknown>[]>("/api/positions"),

  // --- APEX engine (:8000) ---

  getDashboardSnapshot: () =>
    fetchApex<{
      type: string;
      account: AccountSnapshot;
      positions: Position[];
      opportunities: OpportunityScore[];
      proposals: TradeProposal[];
      events: AuditEvent[];
      _is_stale?: boolean;
      _data_age_seconds?: number;
      timestamp?: string;
    }>("/api/dashboard/snapshot"),

  getAccount: () => fetchApex<AccountSnapshot>("/account"),

  getAccountHistory: (days: number = 30) =>
    fetchApex<Record<string, unknown>[]>(`/account/history?days=${days}`),

  getPositions: () => fetchApex<Position[]>("/positions"),

  getClosedPositions: () => fetchApex<Position[]>("/positions/closed"),

  getProposals: () => fetchApex<TradeProposal[]>("/proposals"),

  getProposalHistory: () => fetchApex<TradeProposal[]>("/proposals/history"),

  getOpportunities: () => fetchApex<OpportunityScore[]>("/opportunities"),

  getArbSummary: () =>
    fetchApex<{
      active_opportunities: number;
      resolved_opportunities: number;
      win_rate: number;
    }>("/api/arb/summary"),

  getPmBrain: () =>
    fetchApex<{
      timestamp: number;
      paper_only: boolean;
      polymarket_paper_enabled: boolean;
      kalshi: { status: string; detail: string; paper_bankroll_usd: number };
      polymarket: { status: string; detail: string; paper_bankroll_usd: number };
      arb: {
        min_net_edge: number;
        relax_orderbook_checks: boolean;
        cached_opportunities: number;
        top_net_edge: number;
        fresh_scan_count: number;
      };
      recent_opportunities: Array<{
        id: string;
        question: string;
        kalshi_ticker: string;
        net_edge: number;
        settlement_match_score: number;
      }>;
      guidance: string;
    }>("/api/pm/brain"),

  getArbBacktest: (lookbackDays: number = 90) =>
    fetchApex<BacktestResult>(`/api/arb/backtest?lookback_days=${lookbackDays}`),

  getEvents: (limit: number = 100) => fetchApex<AuditEvent[]>(`/events?limit=${limit}`),

  getRiskMetrics: () => fetchApex<Record<string, unknown>>("/api/risk/metrics"),

  getPerformanceAnalytics: () => fetchApex<Record<string, unknown>>("/analytics/performance"),

  getSignalQuality: () =>
    fetchApex<{
      by_source: Record<string, { count: number; avg_conviction: number; approval_rate: number }>;
      by_conviction: Record<string, { count: number; approval_rate: number }>;
    }>("/analytics/signal-quality"),

  runAgentsConsensus: (proposal: Record<string, unknown>) =>
    fetchApex<Record<string, unknown>>("/api/agents/consensus", {
      method: "POST",
      body: JSON.stringify({ proposal }),
    }),

  listArbOpportunities: (limit = 200) =>
    fetchApex<Record<string, unknown>[]>(`/api/arb/opportunities?limit=${limit}`),

  getMlStatus: () => fetchApex<Record<string, unknown>>("/api/ml/status"),

  mlExport: () =>
    fetchApex<Record<string, unknown>>("/api/ml/export", { method: "POST" }),

  mlTrain: () =>
    fetchApex<Record<string, unknown>>("/api/ml/train", { method: "POST" }),

  mlEvaluate: (force = false) =>
    fetchApex<Record<string, unknown>>(
      `/api/ml/evaluate${force ? "?force=true" : ""}`,
      { method: "POST" }
    ),

  mlRunCycle: () =>
    fetchApex<Record<string, unknown>>("/api/ml/run-cycle", { method: "POST" }),

  getChart: (symbol: string, timeframe: string = "1D") =>
    fetchApex<ChartBar[]>(`/chart/${symbol}?timeframe=${timeframe}`),

  getOptionChain: (symbol: string) => fetchApex<OptionChain>(`/options/${symbol}`),

  submitOrder: (order: Record<string, unknown>) =>
    fetchApex<{ order_id: string }>("/orders", {
      method: "POST",
      body: JSON.stringify(order),
    }),

  cancelOrder: (orderId: string) =>
    fetchApex<{ success: boolean }>(`/orders/${orderId}`, { method: "DELETE" }),

  getIntegrations: (force = false) =>
    fetchApex<Record<string, unknown>>(force ? "/integrations?force=true" : "/integrations"),

  getApexHealth: () => fetchApex<ApexHealthPayload>("/health"),

  refreshEngine: () =>
    fetchApex<{ status: string; timestamp: string; is_stale: boolean }>("/refresh", {
      method: "POST",
    }),

  /** Settings compatibility — APEX /api/health alias */
  getHealth: () => fetchApex<HealthData>("/api/health"),
};
