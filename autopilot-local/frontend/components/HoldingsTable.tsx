export function HoldingsTable({
  holdings,
}: {
  holdings: Array<{
    ticker: string;
    weight_pct: number;
    shares: number;
    price: number;
    value_usd: number;
  }>;
}) {
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-700">
      <table className="min-w-full text-sm">
        <thead className="bg-slate-800/80 text-left text-slate-400">
          <tr>
            <th className="px-4 py-2">Ticker</th>
            <th className="px-4 py-2">Weight</th>
            <th className="px-4 py-2">Price</th>
            <th className="px-4 py-2">Value (sim)</th>
          </tr>
        </thead>
        <tbody>
          {holdings.map((h) => (
            <tr key={h.ticker} className="border-t border-slate-800">
              <td className="px-4 py-2 font-mono font-semibold">{h.ticker}</td>
              <td className="px-4 py-2">{h.weight_pct.toFixed(1)}%</td>
              <td className="px-4 py-2">${h.price.toFixed(2)}</td>
              <td className="px-4 py-2">${h.value_usd.toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
