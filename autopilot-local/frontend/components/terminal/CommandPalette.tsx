"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

const COMMANDS = [
  { label: "Overview", href: "/dashboard" },
  { label: "Trading", href: "/dashboard/trading" },
  { label: "Positions", href: "/dashboard/positions" },
  { label: "Signals", href: "/dashboard/opportunities" },
  { label: "Autopilot", href: "/dashboard/autopilot" },
  { label: "Arb Radar", href: "/dashboard/arb-radar" },
  { label: "Analytics", href: "/dashboard/analytics" },
  { label: "Live Feed", href: "/dashboard/live" },
  { label: "Marketplace", href: "/dashboard/marketplace" },
  { label: "Polymarket", href: "/dashboard/polymarket" },
  { label: "Settings", href: "/dashboard/settings" },
];

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const router = useRouter();

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen((o) => !o);
      }
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const filtered = COMMANDS.filter((c) =>
    c.label.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div
      id="cmd-palette"
      className={`cmd-palette${open ? " open" : ""}`}
      data-cmd-close
      onClick={(e) => {
        if (e.target === e.currentTarget) setOpen(false);
      }}
    >
      <div className="cmd-dialog">
        <input
          className="cmd-input"
          placeholder="Go to page or action…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          autoFocus={open}
        />
        <div className="cmd-list">
          {filtered.map((cmd) => (
            <div
              key={cmd.href}
              className="cmd-item"
              role="button"
              tabIndex={0}
              onClick={() => {
                router.push(cmd.href);
                setOpen(false);
                setQuery("");
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  router.push(cmd.href);
                  setOpen(false);
                }
              }}
            >
              <span>{cmd.label}</span>
              <span style={{ color: "var(--text-dim)" }}>→</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export function useCommandPaletteTrigger() {
  return { openPalette: () => document.getElementById("cmd-palette")?.classList.add("open") };
}
