export function PositionRow({
  ticker,
  qty,
  avgEntry,
  currentPrice,
  unrealizedPl,
  portfolioId,
}: {
  ticker: string;
  qty: number;
  avgEntry: number;
  currentPrice: number;
  unrealizedPl: number;
  portfolioId: string;
}) {
  const positive = unrealizedPl >= 0;
  return (
    <tr className="border-t border-slate-800">
      <td className="px-4 py-2 font-mono font-semibold">{ticker}</td>
      <td className="px-4 py-2">{qty}</td>
      <td className="px-4 py-2">${avgEntry.toFixed(2)}</td>
      <td className="px-4 py-2">${currentPrice.toFixed(2)}</td>
      <td className={`px-4 py-2 font-mono ${positive ? "text-apex-green" : "text-apex-red"}`}>
        {positive ? "+" : ""}${unrealizedPl.toFixed(2)}
      </td>
      <td className="px-4 py-2 text-slate-400">{portfolioId || "—"}</td>
    </tr>
  );
}
