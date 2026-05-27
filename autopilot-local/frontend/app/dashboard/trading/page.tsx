"use client";

import { useEffect, useState } from "react";
import { api, type ChartBar, type OptionChain, type OptionContract } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { ApexChart } from "@/components/chart/ApexChart";
import { formatCurrency, formatNumber, cn, getChangeColor } from "@/lib/utils";
import { PageHeader, Card, CardHeader, KpiCard, Tabs, EmptyState } from "@/components/terminal/ui";

const timeframes = ["1m", "5m", "15m", "1h", "4h", "1D", "1W"];

function OptionChainTable({ contracts }: { contracts: OptionContract[] }) {
  return (
    <div className="table-wrap" style={{ maxHeight: 420 }}>
      <table>
        <thead>
          <tr>
            <th>Strike</th>
            <th>Bid</th>
            <th>Ask</th>
            <th>Last</th>
            <th>IV</th>
            <th>Δ</th>
            <th>Γ</th>
            <th>Θ</th>
            <th>V</th>
          </tr>
        </thead>
        <tbody>
          {contracts.slice(0, 12).map((contract) => (
            <tr key={contract.strike}>
              <td className="mono">{formatNumber(contract.strike)}</td>
              <td>{formatNumber(contract.bid)}</td>
              <td>{formatNumber(contract.ask)}</td>
              <td className={cn(getChangeColor(contract.change))}>{formatNumber(contract.last)}</td>
              <td>{formatNumber(contract.implied_volatility * 100)}%</td>
              <td>{formatNumber(contract.delta, 3)}</td>
              <td>{formatNumber(contract.gamma, 4)}</td>
              <td>{formatNumber(contract.theta, 2)}</td>
              <td>{formatNumber(contract.vega, 2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function TradingPage() {
  const { selectedSymbol, setSelectedSymbol, positions } = useAppStore();
  const [selectedTimeframe, setSelectedTimeframe] = useState("1D");
  const [chartData, setChartData] = useState<ChartBar[]>([]);
  const [optionChain, setOptionChain] = useState<OptionChain | null>(null);
  const [loading, setLoading] = useState(false);
  const [optionsTab, setOptionsTab] = useState("Calls");

  const defaultSymbol = selectedSymbol || positions[0]?.symbol || "NVDA";
  const lastBar = chartData[chartData.length - 1];
  const recent = chartData.slice(-30);

  useEffect(() => {
    async function loadChart() {
      if (!defaultSymbol) return;
      setLoading(true);
      try {
        const data = await api.getChart(defaultSymbol, selectedTimeframe);
        setChartData(data);
      } catch (error) {
        console.error("Failed to load chart:", error);
        setChartData([]);
      } finally {
        setLoading(false);
      }
    }
    loadChart();
  }, [defaultSymbol, selectedTimeframe]);

  useEffect(() => {
    async function loadOptions() {
      if (!defaultSymbol) return;
      try {
        const chain = await api.getOptionChain(defaultSymbol);
        setOptionChain(chain);
      } catch (error) {
        console.error("Failed to load options:", error);
        setOptionChain(null);
      }
    }
    loadOptions();
  }, [defaultSymbol]);

  const symbolOptions = [
    defaultSymbol,
    ...positions.map((p) => p.symbol).filter((s) => s !== defaultSymbol),
  ];

  return (
    <DashboardLayout showRightPanel defaultSymbol={defaultSymbol}>
      <PageHeader
        title="Trading"
        subtitle={
          <>
            <select
              value={defaultSymbol}
              onChange={(e) => setSelectedSymbol(e.target.value)}
              className="mono"
              style={{
                background: "var(--surface-2)",
                border: "1px solid var(--border)",
                borderRadius: 6,
                padding: "4px 8px",
                color: "var(--text)",
                marginRight: 8,
              }}
            >
              {symbolOptions.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
            {lastBar && (
              <span>
                {formatCurrency(lastBar.close)}{" "}
                <span className="pill live" style={{ marginLeft: 6 }}>
                  Live
                </span>
              </span>
            )}
          </>
        }
        actions={
          <div className="tabs" style={{ margin: 0 }}>
            {timeframes.map((tf) => (
              <button
                key={tf}
                type="button"
                data-testid={`tf-${tf}`}
                className={cn("tab", selectedTimeframe === tf && "active")}
                onClick={() => setSelectedTimeframe(tf)}
              >
                {tf}
              </button>
            ))}
          </div>
        }
      />

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 340px",
          gap: 14,
          alignItems: "start",
        }}
      >
        <div>
          <Card>
            <CardHeader
              title={`Price · ${defaultSymbol}`}
              action={
                <span
                  data-testid="chart-timeframe"
                  style={{ fontSize: 12, color: "var(--text-muted)" }}
                >
                  {selectedTimeframe}
                </span>
              }
            />
            {loading ? (
              <EmptyState message="Loading chart…" />
            ) : chartData.length > 0 ? (
              <ApexChart data={chartData} height={420} showVolume />
            ) : (
              <div className="chart-area" style={{ height: 420 }} />
            )}
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 12 }}>
              <span className="pill">Bars {chartData.length}</span>
              {optionChain?.expiry && <span className="pill">Opt exp {optionChain.expiry}</span>}
            </div>
          </Card>

          <div className="grid grid-kpi" style={{ marginTop: 14, gridTemplateColumns: "repeat(4, 1fr)" }}>
            <KpiCard
              title="Last"
              value={lastBar ? formatCurrency(lastBar.close) : "—"}
            />
            <KpiCard
              title="High"
              value={
                recent.length ? formatCurrency(Math.max(...recent.map((b) => b.high))) : "—"
              }
            />
            <KpiCard
              title="Low"
              value={recent.length ? formatCurrency(Math.min(...recent.map((b) => b.low))) : "—"}
            />
            <KpiCard
              title="Volume"
              value={lastBar ? formatNumber(lastBar.volume || 0) : "—"}
            />
          </div>
        </div>

        <Card>
          <CardHeader
            title={optionChain ? `Options · ${optionChain.expiry}` : "Options chain"}
          />
          {optionChain ? (
            <>
              <Tabs
                items={["Calls", "Puts"]}
                active={optionsTab}
                onChange={setOptionsTab}
              />
              <OptionChainTable
                contracts={optionsTab === "Calls" ? optionChain.calls : optionChain.puts}
              />
            </>
          ) : (
            <EmptyState message="No options data" />
          )}
        </Card>
      </div>
    </DashboardLayout>
  );
}
