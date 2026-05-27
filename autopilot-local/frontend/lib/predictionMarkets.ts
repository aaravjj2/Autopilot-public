import type { ArbOpportunity } from "@/types/arb";
import { getApexApiUrl, getApexDirectUrl } from "@/lib/backend-urls";

export type KalshiBook = {
  execution_mode?: string;
  bankroll_usd: number;
  buying_power_usd: number;
  open_positions: number;
  unrealized_pl: number;
  daily_pl: number;
  status: { status: string; detail: string; paper_bankroll_usd?: number };
  positions: Array<{
    id: string;
    ticker: string;
    question: string;
    side: string;
    stake_usd: number;
    entry_price: number;
    unrealized_pl: number;
    opened_at?: string;
  }>;
  trades: Array<{
    id: string;
    ticker: string;
    side: string;
    stake_usd: number;
    status: string;
    executed_at?: string;
  }>;
  active_markets: Array<{
    id: string;
    question: string;
    kalshi_ticker: string;
    net_edge: number;
    settlement_match_score: number;
  }>;
};

export type PolymarketBook = {
  summary: {
    bankroll_usd: number;
    open_positions: number;
    unrealized_pl: number;
    daily_pl: number;
    buying_power_usd: number;
  };
  status: { status: string; detail: string; paper_bankroll_usd?: number };
  positions: Array<{
    id: string | number;
    market_id: string | number;
    question: string;
    side: string;
    stake_usd: number;
    entry_price: number;
    unrealized_pl: number;
    opened_at?: string | null;
  }>;
  trades: Array<{
    id: string | number;
    market_id: string | number;
    side: string;
    stake_usd: number;
    status: string;
    executed_at?: string | null;
  }>;
  equity_curve: Array<{ date: string; bankroll_usd: number }>;
};

async function fetchBook<T>(path: string): Promise<T> {
  const res = await fetch(`${getApexApiUrl()}${path}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`${path} failed (${res.status})`);
  }
  return res.json() as Promise<T>;
}

export type PmAgentsStatus = {
  execution_mode?: string;
  kalshi_demo_trading_enabled?: boolean;
  kalshi_demo_broker?: boolean;
  kalshi_base_url?: string;
  kalshi_paper_broker: boolean;
  polymarket_paper_broker: boolean;
  alpaca_paper_trade: boolean;
  polymarket_paper_enabled: boolean;
  polymarket_automated_events: boolean;
  last_kalshi_cycle?: Record<string, unknown>;
};

export type WorldCupOpportunity = {
  id: string;
  venue: string;
  question: string;
  market_yes_ask: number;
  fair_prob?: number;
  model_edge?: number;
  net_edge?: number;
  final_score?: number;
  kalshi_ticker?: string;
  poly_market_id?: string;
};

export type WorldCupStatus = {
  enabled: boolean;
  execution_mode: string;
  opportunities_cached: number;
  min_model_edge: number;
  use_poisson_model?: boolean;
  confidence_tiers?: string;
  simulation_endpoint?: string;
  last_cycle?: Record<string, unknown>;
};

export type WorldCupSimulation = {
  paper: boolean;
  read_only: boolean;
  model_version: string;
  n_sims: number;
  top_teams: Array<{ team: string; win_probability: number }>;
};

export const predictionMarkets = {
  getKalshiBook: () => fetchBook<KalshiBook>("/api/kalshi/book"),
  getPolymarketBook: () => fetchBook<PolymarketBook>("/api/polymarket/book"),
  getAgentsStatus: () => fetchBook<PmAgentsStatus>("/api/pm/agents/status"),
  runPolymarketAgents: () =>
    fetch(`${getApexDirectUrl()}/api/pm/polymarket/run-agents`, { method: "POST" }).then(async (res) => {
      if (!res.ok) throw new Error(`run-agents failed (${res.status})`);
      return res.json();
    }),
  runKalshiAgents: () =>
    fetch(`${getApexDirectUrl()}/api/pm/kalshi/run-agents`, { method: "POST" }).then(async (res) => {
      if (!res.ok) throw new Error(`kalshi agents failed (${res.status})`);
      return res.json();
    }),
  runBothAgents: () =>
    fetch(`${getApexDirectUrl()}/api/pm/agents/run`, { method: "POST" }).then(async (res) => {
      if (!res.ok) throw new Error(`pm agents failed (${res.status})`);
      return res.json();
    }),
  placeKalshiPaper: (body: { ticker: string; stake_usd?: number; price?: number; question?: string }) =>
    fetch(`${getApexApiUrl()}/api/kalshi/paper-trade`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then(async (res) => {
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || `kalshi trade failed (${res.status})`);
      return data;
    }),
  placePolymarketPaper: (body: {
    market_id: string;
    outcome?: string;
    stake_usd?: number;
    price?: number;
    question?: string;
  }) =>
    fetch(`${getApexApiUrl()}/api/polymarket/paper-trade`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then(async (res) => {
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || `polymarket trade failed (${res.status})`);
      return data;
    }),
  listArbOpportunities: () =>
    fetch(`${getApexApiUrl()}/api/arb/opportunities?limit=50`, { cache: "no-store" }).then(
      async (res) => {
        if (!res.ok) throw new Error("arb opportunities unavailable");
        return res.json() as Promise<ArbOpportunity[]>;
      }
    ),
  getWorldCupStatus: () => fetchBook<WorldCupStatus>("/api/world-cup/status"),
  getWorldCupOpportunities: () =>
    fetchBook<WorldCupOpportunity[]>("/api/world-cup/opportunities?limit=80"),
  getWorldCupSimulation: (n = 1000) =>
    fetchBook<WorldCupSimulation>(`/api/world-cup/simulation?n=${n}`),
  runWorldCupCycle: () =>
    fetch(`${getApexDirectUrl()}/api/world-cup/run-cycle`, { method: "POST" }).then(async (res) => {
      if (!res.ok) throw new Error(`world cup cycle failed (${res.status})`);
      return res.json() as Promise<Record<string, unknown>>;
    }),
};
