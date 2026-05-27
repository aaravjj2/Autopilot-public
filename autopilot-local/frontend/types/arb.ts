export interface ArbOpportunity {
  id: string;
  kalshi_ticker: string;
  poly_market_id: string;
  question: string;
  kalshi_title: string;
  poly_title: string;
  kalshi_yes_ask: number;
  poly_no_ask: number;
  gross_spread: number;
  net_edge: number;
  settlement_match_score: number;
  settlement_flags: string[];
  volume_kalshi: number;
  volume_poly: number;
  category: string;
  kelly_fraction: number;
  detection_ts?: string;
  resolution_ts?: string;
  outcome?: string;
  pnl?: number;
}

export interface ArbThesis {
  arb_id: string;
  one_liner: string;
  confidence: string;
  bull_case: string;
  bear_case: string;
  recommended_leg: string;
  risk_flags: string[];
  settlement_explanation: string;
  llm_provider: string;
}

export interface BacktestCategoryStat {
  category: string;
  n_trades: number;
  win_rate: number;
  avg_edge: number;
  total_pnl: number;
}

export interface BacktestResult {
  n_trades: number;
  win_rate: number;
  sharpe: number;
  total_pnl: number;
  avg_net_edge: number;
  avg_hold_days: number;
  edge_per_day: [string, number][];
  annualized_roc: number;
  slippage_adjusted_sharpe: number;
  max_drawdown: number;
  per_category_stats: BacktestCategoryStat[];
}
