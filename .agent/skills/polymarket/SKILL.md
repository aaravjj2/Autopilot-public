---
name: polymarket
description: >
  Use this skill for all Polymarket Gamma REST API integration work: fetching active
  liquid markets, parsing outcomePrices, computing NO-side ask prices, and filtering
  by volume. Also covers the existing polymarket_gamma_public.py patterns in APEX.
  Trigger when adding or debugging Polymarket market fetching for arb scanning.
compatibility: Antigravity CLI (agy), Claude Code, Gemini CLI
---

# Polymarket Gamma REST Skill

## Base URL

```
GAMMA_BASE = "https://gamma-api.polymarket.com"
```

No auth required for market discovery. For trading (CLOB), use CLOB API with separate auth.

---

## Key Endpoints

```python
# GET /markets — active market list
# GET /markets/{condition_id} — single market detail
# GET /events — event list
# GET /events/{event_id} — event detail with child markets

import httpx
GAMMA_BASE = "https://gamma-api.polymarket.com"

def fetch_gamma_markets(
    active: bool = True,
    limit: int = 200,
    min_volume: float = 10_000,
) -> list[dict]:
    resp = httpx.get(
        f"{GAMMA_BASE}/markets",
        params={"active": str(active).lower(), "closed": "false", "limit": limit},
        timeout=20,
    )
    resp.raise_for_status()
    markets = resp.json()

    result = []
    for m in markets:
        vol = float(m.get("volume24hr") or m.get("volume") or 0)
        if vol < min_volume:
            continue
        result.append(m)
    return result
```

---

## Price Parsing (Critical Detail)

Polymarket returns `outcomePrices` as a **JSON-encoded string**, not a native array:

```python
import json

def parse_outcome_prices(market: dict) -> tuple[float, float]:
    """
    Returns (yes_price, no_price) where both are 0.0–1.0.
    outcomePrices is either:
      - a JSON string: '["0.62", "0.38"]'
      - a native list:  [0.62, 0.38]
    The first element is YES price, second is NO.
    """
    raw = market.get("outcomePrices")
    if isinstance(raw, str):
        try:
            prices = json.loads(raw)
        except json.JSONDecodeError:
            return 0.5, 0.5
    elif isinstance(raw, list):
        prices = raw
    else:
        return 0.5, 0.5

    if len(prices) >= 2:
        yes = float(prices[0])
        no  = float(prices[1])
    elif len(prices) == 1:
        yes = float(prices[0])
        no  = 1.0 - yes
    else:
        return 0.5, 0.5

    return round(yes, 4), round(no, 4)
```

---

## Enriched Market Fetch for Arb

```python
def fetch_arb_ready_markets(min_volume: float = 10_000) -> list[dict]:
    """
    Fetch markets and enrich with bestAsk_yes and bestAsk_no fields
    for direct use in ArbEngine comparison.
    """
    raw = fetch_gamma_markets(min_volume=min_volume)
    result = []
    for m in raw:
        yes_price, no_price = parse_outcome_prices(m)
        # For arb: we buy the NO side on Poly, so we need the NO ask price
        # In Polymarket's AMM model, the ask is approximately the complement
        # of the best bid. For simplicity, use outcomePrices as market mid.
        # For production: pull CLOB orderbook via https://clob.polymarket.com/book
        m["bestAsk_yes"] = yes_price
        m["bestAsk_no"]  = no_price
        m["id"]          = m.get("conditionId") or m.get("id", "")
        result.append(m)
    return result
```

---

## CLOB Orderbook (Production Accuracy)

For precise best-ask prices in production, use the CLOB API:

```python
CLOB_BASE = "https://clob.polymarket.com"

def fetch_clob_orderbook(token_id: str) -> dict:
    """
    token_id is the YES outcome token ID (from market.clobTokenIds[0]).
    Returns: {bids: [[price, size], ...], asks: [[price, size], ...]}
    """
    resp = httpx.get(
        f"{CLOB_BASE}/book",
        params={"token_id": token_id},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()

def get_best_ask_no(market: dict) -> float:
    """Get precise NO-side best ask from CLOB orderbook."""
    token_ids = market.get("clobTokenIds", [])
    if len(token_ids) < 2:
        # Fallback to complement of YES mid price
        _, no_price = parse_outcome_prices(market)
        return no_price
    try:
        # NO outcome is second token
        no_token = token_ids[1]
        ob = fetch_clob_orderbook(no_token)
        asks = ob.get("asks", [])
        if asks:
            return float(asks[0][0])   # best ask (lowest)
    except Exception:
        pass
    _, no_price = parse_outcome_prices(market)
    return no_price
```

---

## Existing APEX Patterns (polymarket_gamma_public.py)

The file `src/apex/integrations/polymarket_gamma_public.py` already has `fetch_active_liquid_markets()`. Extend it rather than replacing it:

```python
# Add to existing function signature:
def fetch_active_liquid_markets(
    min_volume: float = 10_000,
    enrich_for_arb: bool = False,        # NEW param
) -> list[dict]:
    ...
    if enrich_for_arb:
        for m in result:
            yes_p, no_p = parse_outcome_prices(m)
            m["bestAsk_yes"] = yes_p
            m["bestAsk_no"]  = no_p
    return result
```

Call from ArbEngine:
```python
poly_markets = fetch_active_liquid_markets(
    min_volume=self.settings.kalshi_min_volume_24h,
    enrich_for_arb=True,
)
```

---

## Common Gotchas

1. `outcomePrices` is a string, not an array — always `json.loads()` it
2. Gamma REST returns `volume` (all-time) and `volume24hr` (recent) — use `volume24hr` for liquidity
3. `conditionId` is the unique ID, not `id` — double-check the field name for each API version
4. Markets with `enableOrderBook: false` have no CLOB data — fall back to outcome prices
5. Binary markets have exactly 2 outcome tokens; categorical markets have more — arb logic only applies to binary
