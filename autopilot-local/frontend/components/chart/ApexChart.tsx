"use client";

import { useEffect, useRef, useState } from "react";
import { createChart, ColorType, IChartApi } from "lightweight-charts";
import type { ChartBar } from "@/lib/api";

interface ApexChartProps {
  data: ChartBar[];
  width?: number | string;
  height?: number | string;
  showVolume?: boolean;
}

function transformData(data: ChartBar[]) {
  return data.map((bar) => ({
    time: (bar.time / 1000) as any,
    open: bar.open,
    high: bar.high,
    low: bar.low,
    close: bar.close,
  }));
}

function transformVolume(data: ChartBar[]) {
  return data.map((bar) => ({
    time: (bar.time / 1000) as any,
    value: bar.volume || 0,
    color: bar.close >= bar.open ? "rgba(34, 197, 94, 0.5)" : "rgba(239, 68, 68, 0.5)",
  }));
}

export function ApexChart({
  data,
  width = "100%",
  height = 500,
  showVolume = true,
}: ApexChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!chartContainerRef.current || !data.length) return;

    setIsLoading(false);

    // Destroy old chart if exists
    if (chartContainerRef.current.innerHTML) {
      chartContainerRef.current.innerHTML = "";
    }

    const chart = createChart(chartContainerRef.current, {
      width: typeof width === "number" ? width : chartContainerRef.current.clientWidth,
      height: typeof height === "number" ? height : 500,
      layout: {
        background: { type: ColorType.Solid, color: "#0a0a0f" },
        textColor: "#9ca3af",
      },
      grid: {
        vertLines: { color: "#1f2937" },
        horzLines: { color: "#1f2937" },
      },
      crosshair: { mode: 1 },
      rightPriceScale: { borderColor: "#374151" },
      timeScale: {
        borderColor: "#374151",
        timeVisible: true,
        secondsVisible: false,
      },
    });

    const candleSeries = chart.addCandlestickSeries({
      upColor: "#22c55e",
      downColor: "#ef4444",
      borderUpColor: "#22c55e",
      borderDownColor: "#ef4444",
      wickUpColor: "#22c55e",
      wickDownColor: "#ef4444",
    });

    candleSeries.setData(transformData(data));

    if (showVolume) {
      const volumeSeries = chart.addHistogramSeries({
        priceFormat: { type: "volume" },
        priceScaleId: "",
      });

      volumeSeries.priceScale().applyOptions({
        scaleMargins: { top: 0.8, bottom: 0 },
      });

      volumeSeries.setData(transformVolume(data));
    }

    chart.timeScale().fitContent();

    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({ width: chartContainerRef.current.clientWidth });
      }
    };

    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
    };
  }, [data, width, height, showVolume]);

  if (isLoading) {
    return (
      <div
        className="chart-area"
        style={{
          width,
          height,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "var(--text-muted)",
        }}
      >
        Loading chart…
      </div>
    );
  }

  return <div ref={chartContainerRef} className="rounded-lg overflow-hidden" style={{ width, height }} />;
}

export function ApexAreaChart({
  data,
  width = "100%",
  height = 200,
  color = "#22c55e",
}: {
  data: { time: number; value: number }[];
  width?: number | string;
  height?: number | string;
  color?: string;
}) {
  const chartContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!chartContainerRef.current || !data.length) return;

    if (chartContainerRef.current.innerHTML) {
      chartContainerRef.current.innerHTML = "";
    }

    const chart = createChart(chartContainerRef.current, {
      width: typeof width === "number" ? width : chartContainerRef.current.clientWidth,
      height: typeof height === "number" ? height : 200,
      layout: {
        background: { type: ColorType.Solid, color: "#0a0a0f" },
        textColor: "#9ca3af",
      },
      grid: {
        vertLines: { color: "#1f2937" },
        horzLines: { color: "#1f2937" },
      },
      rightPriceScale: { borderColor: "#374151" },
      timeScale: { borderColor: "#374151" },
    });

    const areaSeries = chart.addAreaSeries({
      lineColor: color,
      topColor: color,
      bottomColor: "rgba(34, 197, 94, 0)",
      lineWidth: 2,
    });

    areaSeries.setData(data.map(d => ({ time: (d.time / 1000) as any, value: d.value })));
    chart.timeScale().fitContent();

    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({ width: chartContainerRef.current.clientWidth });
      }
    };

    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
    };
  }, [data, width, height, color]);

  return <div ref={chartContainerRef} className="rounded-lg overflow-hidden" style={{ width, height }} />;
}