"""Main loop. Run this to start the WC2026 autopilot."""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone

import requests

from agent.claude_client import call_claude
from agent.decision_engine import make_decision
from agent.prompt_builder import build_prompt
from calibration.tracker import log_decision
from config import bootstrap_env, get_db_connection
from context.assembler import assemble_context
from db.schema import init_db
from ingestion.market_fetcher import POLYMARKET_ENDPOINTS, fetch_all_wc_markets, snapshot_markets


def _banner(bankroll: float, open_positions: int) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return (
        "══════════════════════════════════════════════════\n"
        f"  WC2026 AUTOPILOT — {now}\n"
        f"  Bankroll: ${bankroll:,.2f} | Open positions: {open_positions}\n"
        "══════════════════════════════════════════════════\n"
    )


def run_once(bankroll: float, dry_run: bool = True, single: str | None = None) -> dict:
    bootstrap_env()
    conn = get_db_connection()
    init_db(conn)

    open_positions: list = []
    print(_banner(bankroll, len(open_positions)))

    markets = fetch_all_wc_markets()
    if single:
        markets = [m for m in markets if m.market_id == single or single.lower() in m.question.lower()]

    total = len(markets)
    k_count = sum(1 for m in markets if m.platform == "kalshi")
    p_count = sum(1 for m in markets if m.platform == "polymarket")
    print(f"Fetching markets... {total} WC2026 markets found ({k_count} Kalshi, {p_count} Polymarket)")

    min_vol = 1000.0
    liquid = [m for m in markets if float(m.volume) >= min_vol]
    print(f"Filtering for liquidity... {len(liquid)} pass threshold\n")

    snapshot_markets(conn, liquid)

    summary = {"bet_yes": 0, "bet_no": 0, "skip": 0, "stake": 0.0, "analyzed": 0}

    for m in liquid:
        summary["analyzed"] += 1
        md = m.to_dict()
        print(f"Analyzing: {md['question']}")
        print(
            f"  Platform: {md['platform'].title()} | Market prob: {md['implied_prob']:.1%} | Volume: ${md['volume']:,.0f}"
        )

        ctx = assemble_context(md, bankroll=bankroll, open_positions=open_positions, db_conn=conn)
        system, prompt = build_prompt(ctx)
        agent_rsp = call_claude(prompt, system)
        decision = make_decision(agent_rsp, ctx)
        log_decision(decision, ctx, conn)

        edge_mark = "✓" if abs(decision["edge"]) >= 0.05 else "(below threshold)"
        print(
            f"  Agent estimate: {decision['agent_estimated_prob']:.1%} | Edge: {decision['edge']:+.1%} {edge_mark}"
        )
        if decision["action"] == "skip":
            print("  Decision: SKIP")
        else:
            print(
                f"  Decision: {decision['action'].replace('_', ' ').upper()} | Stake: ${decision['stake']:.2f} (Kelly {decision['kelly_fraction']:.1%})"
            )
            kf = decision.get("key_factors") or []
            if kf:
                print(f"  Key factors: {', '.join(kf[:3])}")
        print("  ──────────────────────────────────────────────\n")

        summary[decision["action"]] += 1
        summary["stake"] += float(decision["stake"])

    if dry_run:
        print("[DRY RUN — no bets placed]")
    print(
        f"Summary: {summary['analyzed']} analyzed | {summary['bet_yes']} BET YES | {summary['bet_no']} BET NO | {summary['skip']} SKIP"
    )
    print(f"Total recommended stake: ${summary['stake']:.2f}")
    return summary


def run_loop(bankroll: float, dry_run: bool = True, single: str | None = None):
    while True:
        run_once(bankroll=bankroll, dry_run=dry_run, single=single)
        if single:
            return
        time.sleep(15 * 60)

def debug_markets() -> None:
    print("\n=== KALSHI RAW RESPONSE SHAPE ===")
    from ingestion.market_fetcher import _kalshi_signed_headers

    headers = _kalshi_signed_headers("GET", "/trade-api/v2/markets") or {}
    if not headers:
        api_key = (os.getenv("KALSHI_API_KEY") or "").strip()
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
    resp = requests.get(
        "https://api.elections.kalshi.com/trade-api/v2/markets",
        params={"limit": 5},
        headers=headers or None,
        timeout=10,
    )
    print(f"Status: {resp.status_code}")
    if resp.ok:
        data = resp.json()
        if isinstance(data, dict):
            print(f"Top-level keys: {list(data.keys())}")
            mkts = data.get("markets") or []
            if mkts:
                print(f"First market keys: {list(mkts[0].keys())}")
                print(f"First market sample: {json.dumps(mkts[0], indent=2)[:500]}")

    print("\n=== POLYMARKET RAW RESPONSE SHAPE ===")
    for url in POLYMARKET_ENDPOINTS:
        try:
            resp = requests.get(url, params={"limit": 5}, timeout=10)
        except Exception as exc:
            print(f"URL: {url} | error: {exc}")
            continue
        print(f"URL: {url} | Status: {resp.status_code}")
        if not resp.ok:
            continue
        data = resp.json()
        if isinstance(data, list) and data:
            print(f"List response. First item keys: {list(data[0].keys())}")
        elif isinstance(data, dict):
            print(f"Dict response. Top-level keys: {list(data.keys())}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--bankroll", type=float, default=1000.0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--single", type=str, default=None)
    parser.add_argument("--debug-markets", action="store_true")
    args = parser.parse_args()
    if args.debug_markets:
        debug_markets()
        raise SystemExit(0)
    run_loop(bankroll=args.bankroll, dry_run=args.dry_run or True, single=args.single)
