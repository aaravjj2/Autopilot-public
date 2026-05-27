"use client";

import Link from "next/link";
import { cn, getChangeColor } from "@/lib/utils";

export function Card({
  children,
  className,
  style,
}: {
  children: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
}) {
  return (
    <div className={cn("card", className)} style={style}>
      {children}
    </div>
  );
}

export function CardHeader({
  title,
  subtitle,
  action,
}: {
  title: string;
  subtitle?: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <div className="card-header">
      <div className="card-title-wrapper">
        <span className="card-title">{title}</span>
        {subtitle && <span className="card-subtitle">{subtitle}</span>}
      </div>
      {action}
    </div>
  );
}

export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: string;
  subtitle?: React.ReactNode;
  actions?: React.ReactNode;
}) {
  return (
    <div className="page-header">
      <div>
        <h2>{title}</h2>
        {subtitle && <div className="page-header-sub">{subtitle}</div>}
      </div>
      {actions && <div style={{ display: "flex", gap: 8 }}>{actions}</div>}
    </div>
  );
}

export function KpiCard({
  title,
  value,
  subValue,
  trend,
}: {
  title: string;
  value: string;
  subValue?: string;
  trend?: "up" | "down" | "neutral";
}) {
  const subClass =
    trend === "up" ? "kpi-up" : trend === "down" ? "kpi-down" : "";
  return (
    <div className="card">
      <div className="card-title">{title}</div>
      <div className="kpi-value">{value}</div>
      {subValue && <div className={cn("kpi-sub", subClass)}>{subValue}</div>}
    </div>
  );
}

export function Tag({
  children,
  variant = "neutral",
}: {
  children: React.ReactNode;
  variant?: "long" | "short" | "neutral";
}) {
  return <span className={cn("tag", `tag-${variant}`)}>{children}</span>;
}

export function StatusBadge({ status }: { status: string }) {
  const s = status.toUpperCase();
  const ok = ["HEALTHY", "RUNNING", "CONNECTED", "ACTIVE", "FILLED"].some((x) =>
    s.includes(x)
  );
  const bad = ["ERROR", "FAILED", "DISCONNECTED", "REJECTED"].some((x) =>
    s.includes(x)
  );
  return (
    <Tag variant={ok ? "long" : bad ? "short" : "neutral"}>{status}</Tag>
  );
}

export function Tabs({
  items,
  active,
  onChange,
  testId,
}: {
  items: string[];
  active: string;
  onChange?: (item: string) => void;
  testId?: string;
}) {
  return (
    <div className="tabs" data-testid={testId}>
      {items.map((item) => (
        <button
          key={item}
          type="button"
          className={cn("tab", active === item && "active")}
          onClick={() => onChange?.(item)}
        >
          {item}
        </button>
      ))}
    </div>
  );
}

export function Pipeline({
  stages,
}: {
  stages: { id: string; label: string; sub: string; active?: boolean }[];
}) {
  return (
    <div className="pipeline">
      {stages.map((s) => (
        <div key={s.id} className={cn("pipe-stage", s.active && "active")}>
          <strong>{s.label}</strong>
          <span>{s.sub}</span>
        </div>
      ))}
    </div>
  );
}

export function DataTable({
  headers,
  rows,
  empty,
}: {
  headers: string[];
  rows: React.ReactNode[][];
  empty?: string;
}) {
  if (rows.length === 0 && empty) {
    return (
      <div className="card" style={{ textAlign: "center", color: "var(--text-dim)" }}>
        {empty}
      </div>
    );
  }
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {headers.map((h) => (
              <th key={h}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              {row.map((cell, j) => (
                <td key={j}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function PlDelta({ value, format }: { value: number; format?: (n: number) => string }) {
  const fmt = format ?? ((n: number) => n.toFixed(2));
  const cls = value > 0 ? "kpi-up" : value < 0 ? "kpi-down" : "";
  return (
    <span className={cn("mono", cls)}>
      {value >= 0 ? "+" : ""}
      {fmt(value)}
    </span>
  );
}

export function LinkButton({
  href,
  children,
  primary,
}: {
  href: string;
  children: React.ReactNode;
  primary?: boolean;
}) {
  return (
    <Link href={href} className={cn("btn", primary && "btn-primary")}>
      {children}
    </Link>
  );
}



export function Btn({
  children,
  primary,
  ...rest
}: {
  children: React.ReactNode;
  primary?: boolean;
} & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button type="button" className={cn("btn", primary && "btn-primary")} {...rest}>
      {children}
    </button>
  );
}

export function EmptyState({ message }: { message: string }) {
  return (
    <p style={{ textAlign: "center", padding: 24, color: "var(--text-dim)" }}>{message}</p>
  );
}
