"use client";

import { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { BacktestResult, BacktestCategoryStat } from "@/types/arb";
import { api } from "@/lib/api";
import { KpiCard, CardHeader, EmptyState } from "@/components/terminal/ui";
import { cn } from "@/lib/utils";

export function BacktestTab() {
  const [data, setData] = useState<BacktestResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setError(null);
    api
      .getArbBacktest(90)
      .then((result) => {
        if (active) setData(result);
      })
      .catch((err: Error) => {
        if (active) setError(err.message);
      });
    return () => {
      active = false;
    };
  }, []);

  if (error) {
    return (
      <div data-testid="backtest-panel">
        <p style={{ fontSize: 13, color: "var(--red)" }}>Backtest unavailable: {error}</p>
      </div>
    );
  }

  if (!data) {
    return (
      <div data-testid="backtest-panel">
        <EmptyState message="Loading backtest…" />
      </div>
    );
  }

  const chartData =
    data.edge_per_day?.map(([date, pnl]: [string, number]) => ({
      date,
      pnl: Number(pnl.toFixed(4)),
    })) || [];

  const stats = [
    { label: "Trades", value: String(data.n_trades) },
    { label: "Win Rate", value: `${(data.win_rate * 100).toFixed(1)}%` },
    {
      label: "Sharpe (Slip Adj)",
      value: data.slippage_adjusted_sharpe
        ? data.slippage_adjusted_sharpe.toFixed(2)
        : data.sharpe.toFixed(2),
    },
    {
      label: "Max Drawdown",
      value: `$${data.max_drawdown ? data.max_drawdown.toFixed(2) : "0.00"}`,
    },
    { label: "Annualized ROC", value: `${(data.annualized_roc * 100).toFixed(1)}%` },
    { label: "Avg Hold", value: `${data.avg_hold_days.toFixed(1)} days` },
  ];

  return (
    <div data-testid="backtest-panel" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <div className="grid grid-kpi" style={{ gridTemplateColumns: "repeat(6, 1fr)" }}>
        {stats.map((stat) => (
          <KpiCard key={stat.label} title={stat.label} value={stat.value} />
        ))}
      </div>

      <div>
        <CardHeader
          title="Cumulative Edge Per Day (90d)"
          action={
            <span style={{ fontSize: 11, color: "var(--text-muted)" }}>
              As of {new Date().toLocaleTimeString()}
            </span>
          }
        />
        <ResponsiveContainer width="100%" height={250}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis dataKey="date" tick={{ fontSize: 10, fill: "var(--text-muted)" }} />
            <YAxis tick={{ fontSize: 10, fill: "var(--text-muted)" }} />
            <Tooltip
              contentStyle={{
                background: "var(--surface-2)",
                border: "1px solid var(--border)",
                borderRadius: 6,
              }}
            />
            <Line type="monotone" dataKey="pnl" stroke="var(--green)" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {data.per_category_stats && data.per_category_stats.length > 0 && (
        <div>
          <CardHeader title="Performance by Category" />
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Category</th>
                  <th>Trades</th>
                  <th>Win Rate</th>
                  <th>Avg Edge</th>
                  <th>Total PNL</th>
                </tr>
              </thead>
              <tbody>
                {[...data.per_category_stats]
                  .sort((a, b) => b.total_pnl - a.total_pnl)
                  .map((cat: BacktestCategoryStat) => (
                    <tr key={cat.category}>
                      <td style={{ fontWeight: 600 }}>{cat.category}</td>
                      <td>{cat.n_trades}</td>
                      <td>{(cat.win_rate * 100).toFixed(1)}%</td>
                      <td className="mono">${cat.avg_edge.toFixed(3)}</td>
                      <td className={cn("mono", cat.total_pnl >= 0 ? "kpi-up" : "kpi-down")}>
                        ${cat.total_pnl.toFixed(2)}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
