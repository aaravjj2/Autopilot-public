"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export function PerformanceChart({
  data,
  benchmarkPct,
}: {
  data: Array<{ date: string; value: number; return_pct: number }>;
  benchmarkPct: number;
}) {
  const chartData = data.map((d) => ({
    date: d.date.slice(5),
    portfolio: d.return_pct,
    benchmark: benchmarkPct,
  }));
  if (!chartData.length) {
    return (
      <p className="text-sm text-slate-500">No performance history yet. Run refresh.</p>
    );
  }
  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={chartData}>
        <CartesianGrid stroke="#334155" strokeDasharray="3 3" />
        <XAxis dataKey="date" stroke="#94a3b8" fontSize={12} />
        <YAxis stroke="#94a3b8" fontSize={12} unit="%" />
        <Tooltip contentStyle={{ background: "#121a24", border: "1px solid #334155" }} />
        <Legend />
        <Line type="monotone" dataKey="portfolio" stroke="#3b82f6" dot={false} name="Portfolio" />
        <Line type="monotone" dataKey="benchmark" stroke="#64748b" dot={false} name="SPY (period)" />
      </LineChart>
    </ResponsiveContainer>
  );
}
