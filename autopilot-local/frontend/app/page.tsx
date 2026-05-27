"use client";

import Link from "next/link";
import {
  LineChart,
  Wallet,
  Zap,
  Target,
  TrendingUp,
  Activity,
  Radio,
  Settings,
  Store,
  Coins,
  Gavel,
} from "lucide-react";

const copyFeatures = [
  { icon: Store, label: "Marketplace", href: "/dashboard/marketplace", desc: "Follow Alpaca pilot portfolios · mirror equity trades" },
];

const predictionFeatures = [
  { icon: Activity, label: "Arb Radar", href: "/dashboard/arb-radar", desc: "Kalshi × Polymarket cross-venue spreads" },
  { icon: Gavel, label: "Kalshi", href: "/dashboard/kalshi", desc: "Event-contract paper book · arb YES legs" },
  { icon: Coins, label: "Polymarket", href: "/dashboard/polymarket", desc: "Prediction-market paper book (not copy trading)" },
];

const features = [
  { icon: LineChart, label: "Trading", href: "/dashboard/trading", desc: "Charts, options chain, greeks, blotter" },
  { icon: Wallet, label: "Positions", href: "/dashboard/positions", desc: "Open & closed book, exposure" },
  { icon: Zap, label: "Autopilot", href: "/dashboard/autopilot", desc: "L0–L4 pipeline & proposals" },
  { icon: Target, label: "Signals", href: "/dashboard/opportunities", desc: "Engine-scored opportunities" },
  { icon: TrendingUp, label: "Analytics", href: "/dashboard/analytics", desc: "Performance & arb backtest" },
  { icon: Radio, label: "Live Feed", href: "/dashboard/live", desc: "Real-time audit stream" },
  { icon: Settings, label: "Settings", href: "/dashboard/settings", desc: "Integrations & risk config" },
];

export default function HomePage() {
  return (
    <div className="landing">
      <header style={{ borderBottom: "1px solid var(--border)", padding: "14px 24px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div className="brand" style={{ padding: 0 }}>
          <div className="brand-mark">AX</div>
          <div>
            <h1>APEX Trading Terminal</h1>
            <p>Autonomous paper-trading · v2</p>
          </div>
        </div>
        <Link href="/dashboard" className="btn btn-primary">
          Launch Terminal
        </Link>
      </header>

      <section className="landing-hero">
        <span className="pill live" style={{ margin: "0 auto 20px", width: "fit-content", display: "inline-flex" }}>
          Engine online · Paper mode
        </span>
        <h2>
          Institutional-grade terminal.
          <br />
          Agentic execution built in.
        </h2>
        <p style={{ maxWidth: 640, margin: "16px auto 32px", color: "var(--text-muted)", fontSize: 17 }}>
          Bloomberg-density UI with AI signals, cross-market arb, options analytics, risk gates, and live audit — wired to real Alpaca data.
        </p>
        <div style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap" }}>
          <Link href="/dashboard" className="btn btn-primary">
            Enter Terminal
          </Link>
          <Link href="/dashboard/arb-radar" className="btn btn-primary">
            Try live demo
          </Link>
          <a
            href="https://github.com/aaravjj2/Autopilot/blob/main/HACKATHON.md"
            className="btn"
            target="_blank"
            rel="noopener noreferrer"
          >
            Hackathon guide
          </a>
          <Link href="/dashboard/arb-radar" className="btn">
            Arb Radar
          </Link>
          <Link href="/dashboard/marketplace" className="btn">
            Marketplace
          </Link>
          <Link href="/dashboard/settings" className="btn">
            Settings
          </Link>
        </div>
      </section>

      <section className="feature-grid">
        <Link href="/dashboard" className="feature-card">
          <div className="card-title">Overview</div>
          <h3 style={{ margin: "8px 0", fontSize: 18 }}>Command Center</h3>
          <p style={{ color: "var(--text-muted)", fontSize: 13 }}>
            KPIs, equity curve, watchlist, heatmap, pipeline, alerts, ⌘K palette.
          </p>
        </Link>
        {features.map((f) => (
          <Link key={f.href} href={f.href} className="feature-card">
            <f.icon size={28} style={{ color: "var(--green)", marginBottom: 12 }} />
            <div className="card-title">{f.label}</div>
            <p style={{ color: "var(--text-muted)", fontSize: 13, marginTop: 8 }}>{f.desc}</p>
          </Link>
        ))}
        {copyFeatures.map((f) => (
          <Link key={f.href} href={f.href} className="feature-card">
            <f.icon size={28} style={{ color: "var(--accent)", marginBottom: 12 }} />
            <div className="card-title">{f.label}</div>
            <p style={{ color: "var(--text-muted)", fontSize: 13, marginTop: 8 }}>{f.desc}</p>
          </Link>
        ))}
        {predictionFeatures.map((f) => (
          <Link key={f.href} href={f.href} className="feature-card">
            <f.icon size={28} style={{ color: "#60a5fa", marginBottom: 12 }} />
            <div className="card-title">{f.label}</div>
            <p style={{ color: "var(--text-muted)", fontSize: 13, marginTop: 8 }}>{f.desc}</p>
          </Link>
        ))}
      </section>

      <footer style={{ textAlign: "center", padding: 32, color: "var(--text-dim)", fontSize: 12, borderTop: "1px solid var(--border)" }}>
        APEX engine :8000 · Next.js terminal UI :3000
      </footer>
    </div>
  );
}
