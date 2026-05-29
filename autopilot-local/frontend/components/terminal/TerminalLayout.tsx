"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { useAppStore } from "@/lib/store";
import { api } from "@/lib/api";
import { formatCurrency, cn } from "@/lib/utils";
import { getApexApiUrl, getApexWsUrl } from "@/lib/backend-urls";
import { useWebSocket } from "@/hooks/useWebSocket";
import { OrderTicket } from "./OrderTicket";
import { NetworkLatencyGauge } from "./NetworkLatencyGauge";
import { DemoBanner } from "@/components/DemoBanner";
import { AuthBar } from "@/components/terminal/AuthBar";
import type { LucideIcon } from "lucide-react";
import {
  LayoutDashboard,
  LineChart,
  Wallet,
  Zap,
  Target,
  TrendingUp,
  Radio,
  Activity,
  Settings,
  Store,
  Coins,
  Shield,
  Brain,
  Landmark,
  FileText,
  Bell,
  Gavel,
  Wifi,
  WifiOff,
} from "lucide-react";

type NavItem = {
  href: string;
  label: string;
  icon: LucideIcon;
  badgeKey?: "signals" | "arb";
};

const NAV_TRADE: NavItem[] = [
  { href: "/dashboard", label: "Overview", icon: LayoutDashboard },
  { href: "/dashboard/trading", label: "Trading", icon: LineChart },
  { href: "/dashboard/positions", label: "Positions", icon: Wallet },
  { href: "/dashboard/opportunities", label: "Signals", icon: Target, badgeKey: "signals" },
];

const NAV_INTEL: NavItem[] = [
  { href: "/dashboard/autopilot", label: "Autopilot", icon: Zap },
  { href: "/dashboard/arb-radar", label: "Arb Radar", icon: Activity, badgeKey: "arb" },
  { href: "/dashboard/risk-management", label: "Risk", icon: Shield },
  { href: "/dashboard/ai-hivemind", label: "Hive-Mind", icon: Brain },
  { href: "/dashboard/analytics", label: "Analytics", icon: TrendingUp },
  { href: "/dashboard/live", label: "Live Feed", icon: Radio },
];

const NAV_COPY: NavItem[] = [
  { href: "/dashboard/marketplace", label: "Marketplace", icon: Store },
];

const NAV_PREDICTION: NavItem[] = [
  { href: "/dashboard/kalshi", label: "Kalshi", icon: Gavel },
  { href: "/dashboard/polymarket", label: "Polymarket", icon: Coins },
  { href: "/dashboard/world-cup", label: "World Cup", icon: Gavel },
];

const NAV_OPS: NavItem[] = [
  { href: "/dashboard/defi-treasury", label: "DeFi", icon: Landmark },
  { href: "/dashboard/fund-admin", label: "Fund", icon: FileText },
];

const NAV_SYSTEM: NavItem[] = [{ href: "/dashboard/settings", label: "Settings", icon: Settings }];

export function TerminalLayout({
  children,
  rightPanel,
  showRightPanel = false,
  topbar,
  defaultSymbol,
}: {
  children: React.ReactNode;
  rightPanel?: React.ReactNode;
  showRightPanel?: boolean;
  topbar?: React.ReactNode;
  defaultSymbol?: string;
}) {
  const pathname = usePathname();
  const {
    account,
    opportunities,
    wsConnected,
    wsLastUpdate,
    setWsConnected,
    handleWsMessage,
    setAccount,
    setPositions,
    setOpportunities,
    setEvents,
  } = useAppStore();
  const [cmdOpen, setCmdOpen] = useState(false);

  const { isConnected } = useWebSocket({
    url: getApexWsUrl("/ws"),
    onMessage: handleWsMessage,
    maxRetries: 50,
  });

  useEffect(() => {
    setWsConnected(isConnected);
  }, [isConnected, setWsConnected]);

  useEffect(() => {
    let cancelled = false;
    const applySnapshot = (snap: Awaited<ReturnType<typeof api.getDashboardSnapshot>>) => {
      if (cancelled) return;
      if (snap.account) setAccount(snap.account);
      setPositions(snap.positions || []);
      setOpportunities(snap.opportunities || []);
      if (snap.events?.length) setEvents(snap.events);
    };
    const load = async () => {
      if (wsConnected) return;
      try {
        applySnapshot(await api.getDashboardSnapshot());
      } catch {
        /* WS or retry will recover */
      }
    };
    load();
    const t = setInterval(load, wsConnected ? 60000 : 10000);
    return () => {
      cancelled = true;
      clearInterval(t);
    };
  }, [wsConnected, setAccount, setPositions, setOpportunities, setEvents]);
  const [arbCount, setArbCount] = useState(0);
  const [statusLine, setStatusLine] = useState({ api: "—", age: 0 });

  useEffect(() => {
    document.documentElement.setAttribute("data-terminal-hydrated", "true");
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setCmdOpen((o) => !o);
      }
      if (e.key === "Escape") setCmdOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    api.getArbSummary().then((s) => setArbCount(s.active_opportunities)).catch(() => {});
    const t = setInterval(() => {
      fetch(`${getApexApiUrl()}/health`)
        .then((r) => r.json())
        .then((h) => setStatusLine({ api: "ok", age: h.data_age_seconds ?? 0 }))
        .catch(() => setStatusLine({ api: "err", age: 0 }));
    }, 15000);
    return () => clearInterval(t);
  }, []);

  const badges: Record<string, number> = {
    signals: opportunities.length,
    arb: arbCount,
  };

  const renderNav = (items: NavItem[]) =>
    items.map((item) => {
      const active = pathname === item.href;
      const badge = item.badgeKey ? badges[item.badgeKey] : 0;
      return (
        <Link
          key={item.href}
          href={item.href}
          className={cn("nav-link", active && "active")}
        >
          <item.icon size={16} />
          {item.label}
          {badge > 0 && <span className="nav-badge">{badge}</span>}
        </Link>
      );
    });

  const sym = defaultSymbol || "NVDA";

  return (
    <>
      <div className={cn("app-shell", showRightPanel && "has-right")}>
        <aside className="sidebar">
          <div className="brand">
            <div className="brand-mark">AX</div>
            <div>
              <h1>APEX Terminal</h1>
              <p>
                {account
                  ? `${formatCurrency(account.equity)} · Paper`
                  : "Paper · Live data"}
              </p>
            </div>
          </div>
          <nav className="nav-group">
            <div className="nav-label">Trade</div>
            {renderNav(NAV_TRADE)}
          </nav>
          <nav className="nav-group">
            <div className="nav-label">Intel</div>
            {renderNav(NAV_INTEL)}
          </nav>
          <nav className="nav-group">
            <div className="nav-label">Copy Trading</div>
            {renderNav(NAV_COPY)}
          </nav>
          <nav className="nav-group">
            <div className="nav-label">Prediction Markets</div>
            {renderNav(NAV_PREDICTION)}
          </nav>
          <nav className="nav-group">
            <div className="nav-label">Ops</div>
            {renderNav(NAV_OPS)}
          </nav>
          <nav className="nav-group">
            <div className="nav-label">System</div>
            {renderNav(NAV_SYSTEM)}
          </nav>
          <div style={{ marginTop: "auto", padding: 10 }}>
            <NetworkLatencyGauge />
            <span className={cn("pill", wsConnected && "live")} style={{ width: "100%", justifyContent: "center", marginTop: 8 }}>
              {wsConnected ? "WS live" : "Polling"}
            </span>
          </div>
        </aside>

        <header className="topbar">
          <button
            type="button"
            className="search-box"
            data-testid="cmd-trigger"
            style={{ cursor: "pointer", border: "none", textAlign: "left" }}
            onClick={() => setCmdOpen(true)}
          >
            <span>⌕</span>
            <span>Search symbol, command…</span>
            <kbd>⌘K</kbd>
          </button>
          {topbar ?? (
            <>
              <span className="pill">NYSE · Regular</span>
              <span className={cn("pill", wsConnected && "live")}>
                {wsConnected ? <Wifi size={12} /> : <WifiOff size={12} />}
                {wsConnected ? " Live" : " Offline"}
              </span>
            </>
          )}
          <AuthBar />
          <button type="button" className="icon-btn" title="Alerts" aria-label="Alerts">
            <Bell size={16} />
          </button>
          <Link href="/dashboard/trading" className="btn btn-primary" data-testid="quick-order">
            Quick Order
          </Link>
        </header>

        <DemoBanner />
        <main className="main">{children}</main>

        {showRightPanel && (
          <aside className="right-panel">
            {rightPanel ?? (
              <>
                <OrderTicket defaultSymbol={sym} />
                <div className="card" style={{ marginTop: 12 }}>
                  <div className="card-title">Alerts</div>
                  <ul style={{ listStyle: "none", fontSize: 12, color: "var(--text-muted)" }}>
                    <li style={{ padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
                      Engine cache auto-refresh 30s
                    </li>
                  </ul>
                </div>
              </>
            )}
          </aside>
        )}

        <footer className="statusbar">
          <span>WS: {wsConnected ? "connected" : "disconnected"}</span>
          <span>API: {statusLine.api === "ok" ? "healthy" : "—"}</span>
          <span>Data age: {Math.round(statusLine.age)}s</span>
          {wsLastUpdate && (
            <span>Updated: {new Date(wsLastUpdate).toLocaleTimeString()}</span>
          )}
          <span style={{ marginLeft: "auto" }}>APEX Terminal</span>
        </footer>
      </div>

      {cmdOpen &&
        typeof document !== "undefined" &&
        createPortal(
          <div
            className="cmd-palette open"
            onClick={(e) => e.target === e.currentTarget && setCmdOpen(false)}
          >
            <CommandPaletteInner onClose={() => setCmdOpen(false)} />
          </div>,
          document.body
        )}
    </>
  );
}

function CommandPaletteInner({ onClose }: { onClose: () => void }) {
  const router = useRouter();
  const [query, setQuery] = useState("");

  const commands = [
    { label: "Overview", href: "/dashboard" },
    { label: "Trading", href: "/dashboard/trading" },
    { label: "Positions", href: "/dashboard/positions" },
    { label: "Signals", href: "/dashboard/opportunities" },
    { label: "Autopilot", href: "/dashboard/autopilot" },
    { label: "Arb Radar", href: "/dashboard/arb-radar" },
    { label: "Analytics", href: "/dashboard/analytics" },
    { label: "Risk", href: "/dashboard/risk-management" },
    { label: "Live Feed", href: "/dashboard/live" },
    { label: "Marketplace", href: "/dashboard/marketplace" },
    { label: "Kalshi", href: "/dashboard/kalshi" },
    { label: "Polymarket", href: "/dashboard/polymarket" },
    { label: "Hive-Mind", href: "/dashboard/ai-hivemind" },
    { label: "Settings", href: "/dashboard/settings" },
  ].filter((c) => c.label.toLowerCase().includes(query.toLowerCase()));

  return (
    <div className="cmd-dialog" data-testid="cmd-dialog">
      <input
        className="cmd-input"
        data-testid="cmd-input"
        placeholder="Go to page…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        autoFocus
      />
      <div className="cmd-list">
        {commands.map((cmd) => (
          <div
            key={cmd.href}
            className="cmd-item"
            role="button"
            tabIndex={0}
            onClick={() => {
              router.push(cmd.href);
              onClose();
            }}
          >
            <span>{cmd.label}</span>
            <span>→</span>
          </div>
        ))}
      </div>
    </div>
  );
}
