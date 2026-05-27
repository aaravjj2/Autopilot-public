---
name: kalshi-api
description: >
  Use this skill for all Kalshi API work: RSA-PSS authentication, market discovery,
  orderbook fetching, ask reconstruction from bid-side reciprocal pricing, and category
  filtering. Trigger when asked to implement or debug KalshiEventClient, Kalshi auth headers,
  or Kalshi orderbook parsing.
compatibility: Antigravity CLI (agy), Claude Code, Gemini CLI
---

# Kalshi API Integration Skill

## Base URL & Auth

```
KALSHI_BASE = "https://external-api.kalshi.com/trade-api/v2"
```

Kalshi uses **RSA-PSS** signing. No OAuth, no Bearer tokens.

```python
# src/apex/integrations/kalshi_adapter.py
import base64
import time
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding

class KalshiAuth:
    def __init__(self, access_key: str, private_key_pem: str):
        self.access_key = access_key
        self._private_key = serialization.load_pem_private_key(
            private_key_pem.encode(), password=None
        )

    def headers(self, method: str, path: str) -> dict[str, str]:
        ts = str(int(time.time() * 1000))  # milliseconds
        msg = (ts + method.upper() + path).encode()
        sig = self._private_key.sign(
            msg,
            asym_padding.PSS(
                mgf=asym_padding.MGF1(hashes.SHA256()),
                salt_length=asym_padding.PSS.DIGEST_LENGTH,
            ),
            hashes.SHA256(),
        )
        return {
            "KALSHI-ACCESS-KEY": self.access_key,
            "KALSHI-ACCESS-TIMESTAMP": ts,
            "KALSHI-ACCESS-SIGNATURE": base64.b64encode(sig).decode(),
            "Content-Type": "application/json",
        }
```

**Note:** For read-only market discovery and orderbook, auth is NOT required.
Auth is only needed for portfolio and order endpoints.

---

## Public Endpoints (No Auth)

```python
import httpx
from dataclasses import dataclass

KALSHI_BASE = "https://external-api.kalshi.com/trade-api/v2"

# List open markets with cursor pagination
def fetch_open_markets(
    category: str | None = None,
    limit: int = 100,
) -> list[dict]:
    markets = []
    cursor = None
    while True:
        params = {"status": "open", "limit": limit}
        if cursor:
            params["cursor"] = cursor
        if category:
            params["category"] = category
        resp = httpx.get(f"{KALSHI_BASE}/markets", params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        markets.extend(data.get("markets", []))
        cursor = data.get("cursor")
        if not cursor:
            break
    return markets

# Get orderbook for a specific ticker
def fetch_orderbook(ticker: str) -> dict:
    resp = httpx.get(
        f"{KALSHI_BASE}/markets/{ticker}/orderbook",
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()
```

---

## CRITICAL: Ask Reconstruction

**Kalshi uses reciprocal pricing. It only exposes bids, not asks.**

```python
def reconstruct_asks(orderbook: dict) -> dict:
    """
    Kalshi orderbook format:
      yes_dollars: [[price_cents, qty], ...]  ← yes bids
      no_dollars:  [[price_cents, qty], ...]  ← no bids

    Prices are in dollars (0.01 to 0.99), NOT cents.
    best_ask_yes = 1.00 - best_bid_no
    best_ask_no  = 1.00 - best_bid_yes
    """
    yes_bids = orderbook.get("yes", [])   # [[price, qty], ...]
    no_bids  = orderbook.get("no", [])

    # best bid = highest price
    best_bid_yes = max((b[0] for b in yes_bids), default=0.0)
    best_bid_no  = max((b[0] for b in no_bids),  default=0.0)

    best_ask_yes = round(1.00 - best_bid_no, 4)
    best_ask_no  = round(1.00 - best_bid_yes, 4)

    return {
        "best_bid_yes": best_bid_yes,
        "best_bid_no": best_bid_no,
        "best_ask_yes": best_ask_yes,
        "best_ask_no": best_ask_no,
    }
```

---

## KalshiEventClient Class (Full)

```python
@dataclass
class KalshiMarket:
    ticker: str
    event_ticker: str
    title: str
    category: str
    best_ask_yes: float   # reconstructed
    best_ask_no: float    # reconstructed
    volume_24h: float
    close_time: str       # ISO 8601

class KalshiEventClient:
    BASE = "https://external-api.kalshi.com/trade-api/v2"
    MACRO_CATEGORIES = ["ECON", "FED", "CRYPTO", "POLITICS", "FINANCE"]

    def __init__(self, settings: "Settings"):
        self.settings = settings
        self._http = httpx.Client(timeout=15)

    def get_macro_markets(self, min_volume: float = 10_000) -> list[KalshiMarket]:
        all_markets = []
        for cat in self.MACRO_CATEGORIES:
            try:
                raw = fetch_open_markets(category=cat)
                all_markets.extend(raw)
            except Exception as e:
                LOGGER.warning("Kalshi fetch failed for category %s: %s", cat, e)

        result = []
        for m in all_markets:
            ticker = m.get("ticker", "")
            try:
                ob = fetch_orderbook(ticker)
                asks = reconstruct_asks(ob)
                vol = float(m.get("volume_24h", 0))
                if vol < min_volume:
                    continue
                result.append(KalshiMarket(
                    ticker=ticker,
                    event_ticker=m.get("event_ticker", ""),
                    title=m.get("title", ""),
                    category=m.get("category", ""),
                    best_ask_yes=asks["best_ask_yes"],
                    best_ask_no=asks["best_ask_no"],
                    volume_24h=vol,
                    close_time=m.get("close_time", ""),
                ))
            except Exception as e:
                LOGGER.warning("Kalshi orderbook failed for %s: %s", ticker, e)
        return result
```

---

## Fee Calculation

```python
KALSHI_FEE_PCT = 0.07  # 7% of winnings

def compute_net_edge(
    kalshi_yes_ask: float,
    poly_no_ask: float,
) -> float:
    """
    Buy YES on Kalshi at kalshi_yes_ask.
    Buy NO on Polymarket at poly_no_ask.
    If YES wins: payout $1.00 from Kalshi minus 7% fee.
    If NO wins:  payout $1.00 from Polymarket (0% fee on Gamma).
    Gross arb = 1.00 - (kalshi_yes_ask + poly_no_ask)
    Net edge accounts for worst-case fee (YES side wins → Kalshi fee).
    """
    gross = 1.00 - (kalshi_yes_ask + poly_no_ask)
    # Conservative: assume YES wins (triggers Kalshi fee)
    fee = KALSHI_FEE_PCT * (1.00 - kalshi_yes_ask)
    return round(gross - fee, 4)
```

---

## Error Handling

```python
from httpx import HTTPStatusError, ReadTimeout

def safe_fetch_orderbook(ticker: str) -> dict | None:
    try:
        return fetch_orderbook(ticker)
    except HTTPStatusError as e:
        if e.response.status_code == 404:
            return None   # market delisted
        LOGGER.warning("Kalshi orderbook HTTP %s for %s", e.response.status_code, ticker)
        return None
    except ReadTimeout:
        LOGGER.warning("Kalshi orderbook timeout for %s", ticker)
        return None
```

---

## Env Vars to Add to Settings

```python
# src/apex/core/config.py
kalshi_access_key: str = Field(default="", alias="KALSHI_ACCESS_KEY")
kalshi_private_key_path: str = Field(default="", alias="KALSHI_PRIVATE_KEY_PATH")
kalshi_min_volume_24h: float = Field(default=10_000.0, alias="KALSHI_MIN_VOLUME_24H")
arb_min_net_edge: float = Field(default=0.02, alias="ARB_MIN_NET_EDGE")
arb_scan_interval_minutes: int = Field(default=5, alias="ARB_SCAN_INTERVAL_MINUTES")
```
