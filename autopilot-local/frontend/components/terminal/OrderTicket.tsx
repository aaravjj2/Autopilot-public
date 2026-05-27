"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export function OrderTicket({ defaultSymbol = "NVDA" }: { defaultSymbol?: string }) {
  const [symbol, setSymbol] = useState(defaultSymbol);
  const [side, setSide] = useState<"buy" | "sell">("buy");
  const [qty, setQty] = useState("10");
  const [orderType, setOrderType] = useState<"market" | "limit">("market");
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    setSymbol(defaultSymbol);
  }, [defaultSymbol]);

  const submit = async () => {
    setSubmitting(true);
    setMessage(null);
    try {
      await api.submitOrder({
        symbol,
        qty: parseFloat(qty),
        side,
        type: orderType,
        time_in_force: "day",
      });
      setMessage("Order submitted");
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Order failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="card">
      <div className="card-title" style={{ marginBottom: 12 }}>
        Order Ticket
      </div>
      <div className="ticket">
        <label>Symbol</label>
        <input value={symbol} onChange={(e) => setSymbol(e.target.value.toUpperCase())} />
        <div className="side-toggle">
          <button
            type="button"
            className={`btn${side === "buy" ? " active-buy" : ""}`}
            onClick={() => setSide("buy")}
          >
            Buy
          </button>
          <button
            type="button"
            className={`btn${side === "sell" ? " active-sell" : ""}`}
            onClick={() => setSide("sell")}
          >
            Sell
          </button>
        </div>
        <label>Qty</label>
        <input type="number" value={qty} onChange={(e) => setQty(e.target.value)} min={1} />
        <label>Type</label>
        <select value={orderType} onChange={(e) => setOrderType(e.target.value as "market" | "limit")}>
          <option value="market">Market</option>
          <option value="limit">Limit</option>
        </select>
        {message && (
          <p style={{ fontSize: 12, marginBottom: 8, color: message.includes("failed") ? "var(--red)" : "var(--green)" }}>
            {message}
          </p>
        )}
        <button type="button" className="btn btn-primary" style={{ width: "100%" }} onClick={submit} disabled={submitting}>
          {submitting ? "Sending…" : "Submit Paper Order"}
        </button>
      </div>
    </div>
  );
}
