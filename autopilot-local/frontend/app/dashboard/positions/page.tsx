"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { PageHeader, Card, KpiCard, Tag, Btn, Tabs } from "@/components/terminal/ui";
import { formatCurrency, cn } from "@/lib/utils";

export default function PositionsPage() {
  const { positions, setPositions, closedPositions, setClosedPositions } = useAppStore();
  const [tab, setTab] = useState("Open");
  const [closing, setClosing] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const [open, closed] = await Promise.all([
          api.getPositions(),
          api.getClosedPositions(),
        ]);
        setPositions(open);
        setClosedPositions(closed);
      } catch (e) {
        console.error(e);
      }
    }
    load();
    const t = setInterval(load, 10000);
    return () => clearInterval(t);
  }, [setPositions, setClosedPositions]);

  const totalPl = positions.reduce((s, p) => s + p.unrealized_pl, 0);

  const closePosition = async (symbol: string, qty: number) => {
    setClosing(symbol);
    try {
      await api.submitOrder({ symbol, qty, side: "sell", type: "market", time_in_force: "day" });
      setPositions(await api.getPositions());
    } catch (e) {
      console.error(e);
    } finally {
      setClosing(null);
    }
  };

  const rows = tab === "Open" ? positions : closedPositions;

  return (
    <DashboardLayout showRightPanel defaultSymbol={positions[0]?.symbol}>
      <PageHeader
        title="Positions"
        subtitle={
          <>
            Unrealized <span className={cn(totalPl >= 0 ? "kpi-up" : "kpi-down")}>{formatCurrency(totalPl)}</span>
          </>
        }
      />

      <div className="grid grid-kpi" style={{ marginBottom: 14, gridTemplateColumns: "repeat(3, 1fr)" }}>
        <KpiCard title="Open" value={String(positions.length)} />
        <KpiCard title="Closed" value={String(closedPositions.length)} />
        <KpiCard
          title="Market value"
          value={formatCurrency(positions.reduce((s, p) => s + p.market_value, 0))}
        />
      </div>

      <Card>
        <Tabs items={["Open", "Closed"]} active={tab} onChange={setTab} testId="positions-tabs" />
        <div className="table-wrap" style={{ maxHeight: "65vh" }}>
          <table>
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Side</th>
                <th>Qty</th>
                <th>Avg</th>
                <th>Price</th>
                <th>P&amp;L</th>
                <th>%</th>
                {tab === "Open" && <th></th>}
              </tr>
            </thead>
            <tbody>
              {rows.map((p) => (
                <tr key={p.symbol}>
                  <td className="mono" style={{ fontWeight: 600 }}>
                    {p.symbol}
                  </td>
                  <td>
                    <Tag variant={p.side === "long" ? "long" : "short"}>{p.side}</Tag>
                  </td>
                  <td>{p.qty}</td>
                  <td>{p.avg_entry_price.toFixed(2)}</td>
                  <td>{p.current_price.toFixed(2)}</td>
                  <td className={cn(p.unrealized_pl >= 0 ? "kpi-up" : "kpi-down")}>
                    {formatCurrency(p.unrealized_pl)}
                  </td>
                  <td>{(p.unrealized_plpc * 100).toFixed(2)}%</td>
                  {tab === "Open" && (
                    <td>
                      <Btn
                        onClick={() => closePosition(p.symbol, Math.abs(p.qty))}
                        disabled={closing === p.symbol}
                      >
                        {closing === p.symbol ? "…" : "Close"}
                      </Btn>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </DashboardLayout>
  );
}
