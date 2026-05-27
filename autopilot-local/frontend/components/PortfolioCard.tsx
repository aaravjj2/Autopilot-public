"use client";

import Link from "next/link";
import { PortfolioCard as PortfolioCardType } from "@/lib/api";
import { formatCurrency, formatPercent, cn } from "@/lib/utils";
import { Tag, Btn } from "@/components/terminal/ui";
import { TrendingUp } from "lucide-react";

export function PortfolioCard({
  portfolio,
  onFollow,
  onUnfollow,
}: {
  portfolio: PortfolioCardType;
  onFollow?: (id: string) => void;
  onUnfollow?: (id: string) => void;
}) {
  const isPositive = portfolio.return_pct >= 0;

  return (
    <div className="card" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <Link
            href={`/dashboard/marketplace/${portfolio.id}`}
            style={{ fontWeight: 600, fontSize: 16, color: "var(--text)" }}
          >
            {portfolio.name}
          </Link>
          <p style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 4 }}>{portfolio.category}</p>
        </div>
        <span className={cn("mono", isPositive ? "kpi-up" : "kpi-down")} style={{ fontSize: 18, fontWeight: 600 }}>
          {isPositive ? "+" : ""}
          {formatPercent(portfolio.return_pct)}
        </span>
      </div>

      <div className="grid grid-kpi" style={{ gridTemplateColumns: "repeat(3, 1fr)", gap: 8 }}>
        <div>
          <div className="card-title">AUM</div>
          <div className="mono">{formatCurrency(portfolio.aum_usd)}</div>
        </div>
        <div>
          <div className="card-title">Holdings</div>
          <div>{portfolio.holdings_count}</div>
        </div>
        <div>
          <div className="card-title">Pilot</div>
          <div style={{ fontSize: 13, overflow: "hidden", textOverflow: "ellipsis" }}>
            {portfolio.pilot_name}
          </div>
        </div>
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        {portfolio.is_following ? (
          <Tag variant="long">Following</Tag>
        ) : (
          <span style={{ fontSize: 12, color: "var(--text-dim)" }}>Not following</span>
        )}
        {portfolio.is_following ? (
          <Btn onClick={() => onUnfollow?.(portfolio.id)}>Unfollow</Btn>
        ) : (
          <Btn primary onClick={() => onFollow?.(portfolio.id)}>
            <TrendingUp size={14} style={{ marginRight: 4 }} />
            Follow
          </Btn>
        )}
      </div>
    </div>
  );
}
