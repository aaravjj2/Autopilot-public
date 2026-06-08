from __future__ import annotations
import difflib
import re
import httpx
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from apex.core.async_bridge import run_sync
from apex.core.config import Settings
from apex.core.logging import get_logger
from apex.domain.exceptions import BrokerCircuitOpenError
from apex.domain.models import ArbOpportunity
from apex.integrations.kalshi_adapter import KalshiEventClient
from apex.integrations.brightdata_intelligence import BrightDataIntelligence
from apex.repositories.sqlite_store import SQLiteStore

LOGGER = get_logger(__name__)
FUZZY_THRESHOLD = 0.72      # Legacy default; prefer settings.arb_match_min_combined_score
MIN_VOLUME_USD   = 10_000   # Both platforms must exceed this
_INTELLIGENCE_TTL_SEC = 300.0
_intelligence_cache: dict[str, tuple[float, dict]] = {}

_TOPIC_KEYWORDS: dict[str, tuple[str, ...]] = {
    "crypto": ("bitcoin", "btc", "ethereum", "eth", "crypto", "solana", "doge"),
    "weather": ("temperature", "weather", "rain", "snow", "degrees", "°f", "°c", "accuweather"),
    "politics": ("president", "election", "congress", "senate", "trump", "biden", "vote"),
    "sports": ("nba", "nfl", "mlb", "wins", "touchdown", "game", "match", "ufc"),
    "macro": ("fed", "cpi", "inflation", "gdp", "recession", "rate", "fomc"),
}


def _topic_tags(title: str) -> set[str]:
    t = title.lower()
    tags: set[str] = set()
    for topic, words in _TOPIC_KEYWORDS.items():
        if any(w in t for w in words):
            tags.add(topic)
    return tags


def _topics_compatible(kalshi_title: str, poly_question: str) -> bool:
    """Reject cross-topic false positives (e.g. NYC weather vs Bitcoin price)."""
    kt, pt = _topic_tags(kalshi_title), _topic_tags(poly_question)
    if not kt or not pt:
        return True
    return bool(kt & pt)


def _tokens(text: str) -> set[str]:
    """Significant word + number tokens used for overlap scoring and the
    candidate-prefilter inverted index."""
    words = set(re.findall(r"[a-z]{3,}", text.lower()))
    nums = set(re.findall(r"\d{2,}", text))
    return words | nums


def _token_overlap_score(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    union = len(ta | tb)
    return inter / union if union else 0.0


def _match_score(
    kalshi_title: str,
    poly_question: str,
    semantic_score: float,
) -> float:
    fuzzy = difflib.SequenceMatcher(None, kalshi_title.lower(), poly_question.lower()).ratio()
    token = _token_overlap_score(kalshi_title, poly_question)
    if semantic_score > 0:
        return (0.45 * semantic_score) + (0.35 * fuzzy) + (0.20 * token)
    return (0.55 * fuzzy) + (0.45 * token)

@dataclass
class ArbEngine:
    settings: Settings
    store: SQLiteStore
    intelligence: BrightDataIntelligence | None = None
    _kalshi_errors: int = 0
    _poly_errors: int = 0
    _kalshi_last_error: float = 0.0
    _poly_last_error: float = 0.0
    CIRCUIT_THRESHOLD: int = 3
    # Latency observability — populated by scan(), read by scan_and_persist.
    _last_fetch_ms: float = 0.0
    _last_match_ms: float = 0.0
    _last_kalshi_count: int = 0
    _last_poly_count: int = 0

    def scan(self) -> list[ArbOpportunity]:
        """Fetch Kalshi + Polymarket markets, find matching pairs, compute arb."""
        if not self.settings.alpaca_paper_trade:
            raise ValueError("M01_PAPER_REQUIRED: live trading not permitted")
        if self.settings.demo_mode:
            from apex.demo.seed_data import demo_opportunities_list

            opps = demo_opportunities_list()
            LOGGER.info("ArbEngine.scan(): DEMO_MODE returning %d seeded opportunities", len(opps))
            return opps
        now = time.time()

        # Fetch Kalshi and Polymarket concurrently — these are independent,
        # network-bound calls and dominate scan latency when run sequentially.
        _t_fetch = time.perf_counter()
        with ThreadPoolExecutor(max_workers=2, thread_name_prefix="arb-fetch") as pool:
            f_kalshi = pool.submit(self._fetch_kalshi, now)
            f_poly = pool.submit(self._fetch_poly, now)
            kalshi_markets = f_kalshi.result()
            poly_markets = f_poly.result()
        self._last_fetch_ms = (time.perf_counter() - _t_fetch) * 1000.0
        self._last_match_ms = 0.0
        self._last_kalshi_count = len(kalshi_markets or [])
        self._last_poly_count = len(poly_markets or [])

        opportunities = []
        seen_pairs: set[tuple[str, str]] = set()
        if not kalshi_markets or not poly_markets:
            return opportunities

        _t_match = time.perf_counter()

        from apex.integrations.chromadb_market_store import ChromaMarketStore
        from apex.services.settlement_auditor import SettlementAuditor
        chroma_store = ChromaMarketStore(self.settings.chromadb_path)
        for poly in poly_markets:
            chroma_store.upsert_market(poly.get("id", ""), poly.get("question", ""), "polymarket")
        for k in kalshi_markets:
            chroma_store.upsert_market(k.ticker, k.title, "kalshi")

        # Build a token -> poly-index inverted index once so each Kalshi title
        # only scores Polymarket candidates that share at least one token,
        # instead of the full O(K*P) cross product.
        poly_index: dict[str, list[int]] = {}
        for idx, p in enumerate(poly_markets):
            p_q = p.get("question", "") or p.get("title", "")
            for tok in _tokens(p_q):
                poly_index.setdefault(tok, []).append(idx)

        # Reuse a single auditor across all candidate pairs instead of
        # constructing one per match (each construction reloads settings/state).
        auditor = SettlementAuditor(settings=self.settings)

        for k in kalshi_markets:
            match = self._combined_match(k.title, poly_markets, chroma_store, poly_index)
            if match is None:
                continue

            poly = match
            from apex.brain.quant_engine import fractional_kelly, net_edge_from_quotes

            poly_no = float(poly.get("bestAsk_no", 1.0))
            gross = round(1.00 - k.best_ask_yes - poly_no, 4)
            net = net_edge_from_quotes(k.best_ask_yes, poly_no)

            if net < self.settings.arb_min_net_edge:
                continue

            verdict = auditor.verify(
                k.title,
                poly.get("question", ""),
                kalshi_market=k,
                poly_market=poly,
                intelligence=self.intelligence,
            )

            opp = ArbOpportunity(
                kalshi_ticker=k.ticker,
                poly_market_id=poly.get("id", ""),
                question=k.title,
                kalshi_title=k.title,
                poly_title=poly.get("question", ""),
                kalshi_yes_ask=k.best_ask_yes,
                poly_no_ask=float(poly.get("bestAsk_no", 1.0)),
                gross_spread=gross,
                net_edge=net,
                settlement_match_score=verdict.match_score,
                settlement_flags=verdict.flags,
                volume_kalshi=k.volume_24h,
                volume_poly=float(poly.get("volume24hr", 0)),
                kelly_fraction=round(
                    fractional_kelly(
                        win_prob=max(0.05, min(0.99, verdict.match_score)),
                        cost=k.best_ask_yes + poly_no,
                        alpha=self.settings.kelly_alpha,
                    ),
                    4,
                ),
            )
            pair = (opp.kalshi_ticker, opp.poly_market_id)
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            opportunities.append(opp)
            LOGGER.info(
                "Arb found: %s | net_edge=%.3f | settlement=%.2f",
                k.ticker, net, verdict.match_score
            )

        self._apply_intelligence_context(opportunities)
        self._last_match_ms = (time.perf_counter() - _t_match) * 1000.0
        LOGGER.info(
            "ArbEngine.scan(): found %d opportunities (fetch=%.0fms match=%.0fms)",
            len(opportunities),
            self._last_fetch_ms,
            self._last_match_ms,
        )
        return opportunities

    def _fetch_kalshi(self, now: float) -> list:
        """Fetch Kalshi macro markets with circuit-breaker handling."""
        try:
            if self._kalshi_errors >= self.CIRCUIT_THRESHOLD:
                cooldown = 60 * (2 ** (self._kalshi_errors - self.CIRCUIT_THRESHOLD))
                if now - self._kalshi_last_error > cooldown:
                    LOGGER.info("Kalshi circuit breaker attempting auto-resume.")
                    self._kalshi_errors = self.CIRCUIT_THRESHOLD - 1
                else:
                    raise BrokerCircuitOpenError("kalshi")
            if self._kalshi_errors < self.CIRCUIT_THRESHOLD:
                kalshi_client = KalshiEventClient(self.settings)
                markets = kalshi_client.get_macro_markets(
                    min_volume=self.settings.kalshi_min_volume_24h,
                    fast=True,
                )
                self._kalshi_errors = 0
                LOGGER.info("Kalshi circuit breaker reset after successful fetch.")
                return markets
            return []
        except BrokerCircuitOpenError:
            LOGGER.critical("Kalshi circuit breaker open. Skipping Kalshi fetch.")
            return []
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (429, 500):
                self._kalshi_errors += 1
                self._kalshi_last_error = now
                LOGGER.error("Kalshi fetch failed with status %s", e.response.status_code)
            else:
                LOGGER.error("Kalshi fetch failed with unexpected status %s", e.response.status_code)
            return []
        except httpx.RequestError as e:
            LOGGER.error("Kalshi request error: %s", e)
            return []

    def _fetch_poly(self, now: float) -> list:
        """Fetch Polymarket liquid markets with circuit-breaker handling."""
        if self._poly_errors >= self.CIRCUIT_THRESHOLD:
            cooldown = 60 * (2 ** (self._poly_errors - self.CIRCUIT_THRESHOLD))
            if now - self._poly_last_error > cooldown:
                LOGGER.info("Polymarket circuit breaker attempting auto-resume.")
                self._poly_errors = self.CIRCUIT_THRESHOLD - 1
            else:
                LOGGER.critical("Polymarket circuit breaker open. Skipping Polymarket fetch.")
                return []
        try:
            from apex.integrations.polymarket_gamma_public import fetch_active_liquid_markets
            poly_min_vol = min(100.0, float(self.settings.kalshi_min_volume_24h))
            markets = fetch_active_liquid_markets(
                limit=int(self.settings.arb_poly_fetch_limit),
                min_volume=poly_min_vol,
                enrich_for_arb=True,
            )
            self._poly_errors = 0
            LOGGER.info("Polymarket circuit breaker reset after successful fetch.")
            return markets
        except BrokerCircuitOpenError:
            LOGGER.critical("Polymarket circuit breaker open. Skipping Polymarket fetch.")
            return []
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (429, 500):
                self._poly_errors += 1
                self._poly_last_error = now
                LOGGER.error("Polymarket fetch failed with status %s", e.response.status_code)
            else:
                LOGGER.error("Polymarket fetch failed with unexpected status %s", e.response.status_code)
            return []
        except httpx.RequestError as e:
            LOGGER.error("Polymarket request error: %s", e)
            return []

    def _apply_intelligence_context(self, opportunities: list[ArbOpportunity]) -> None:
        if not opportunities or self.intelligence is None:
            return
        try:
            budget = run_sync(self.intelligence.check_session_budget())
        except Exception as exc:
            LOGGER.warning("BrightData budget check failed: %s", exc)
            return
        if not budget.get("ok", False):
            LOGGER.warning("BrightData budget exhausted; skipping intelligence context")
            return
        seen: set[str] = set()
        now = time.time()
        for opp in opportunities:
            if opp.net_edge <= 0.03:
                continue
            if opp.kalshi_ticker in seen:
                continue
            seen.add(opp.kalshi_ticker)
            cached = _intelligence_cache.get(opp.kalshi_ticker)
            if cached and (now - cached[0]) < _INTELLIGENCE_TTL_SEC:
                context = cached[1]
            else:
                try:
                    context = run_sync(
                        self.intelligence.get_market_context(
                            opp.kalshi_title,
                            opp.poly_title,
                            self._hours_to_resolution(opp),
                        )
                    )
                except Exception as exc:
                    LOGGER.warning("BrightData market context failed for %s: %s", opp.kalshi_ticker, exc)
                    context = {}
                _intelligence_cache[opp.kalshi_ticker] = (now, context)
            opp.web_context = context or None
            risk_signals = list((context or {}).get("risk_signals") or [])
            for signal in risk_signals:
                opp.settlement_flags.append(signal)
                LOGGER.info("BrightData risk signal on %s: %s", opp.kalshi_ticker, signal)
            reduction = min(0.005 * len(risk_signals), 0.02)
            opp.net_edge = max(0.0, round(opp.net_edge - reduction, 4))

    @staticmethod
    def _hours_to_resolution(opp: ArbOpportunity) -> float:
        if opp.resolution_ts is None:
            return 24.0
        return max(0.0, (opp.resolution_ts.timestamp() - time.time()) / 3600.0)

    def _combined_match(
        self,
        kalshi_title: str,
        poly_markets: list[dict],
        chroma_store,
        poly_index: dict[str, list[int]] | None = None,
    ) -> dict | None:
        """Combine fuzzy, token, and semantic match to find best pair."""
        semantic_matches = chroma_store.find_semantic_match(kalshi_title, "kalshi", top_k=5)
        semantic_map = dict(semantic_matches)
        min_score = float(self.settings.arb_match_min_combined_score)

        # Restrict scoring to a candidate set: poly markets sharing a token with
        # the Kalshi title (via the inverted index) plus any semantic hits. This
        # collapses the per-title work from O(P) to O(candidates) on large books.
        if poly_index is not None:
            cand_idx: set[int] = set()
            for tok in _tokens(kalshi_title):
                hits = poly_index.get(tok)
                if hits:
                    cand_idx.update(hits)
            candidates: list[dict] = [poly_markets[i] for i in cand_idx]
            if semantic_map:
                seen_ids = {c.get("id", "") for c in candidates}
                for p in poly_markets:
                    pid = p.get("id", "")
                    if pid in semantic_map and pid not in seen_ids:
                        candidates.append(p)
        else:
            candidates = poly_markets

        best_match = None
        best_score = 0.0

        for p in candidates:
            p_q = p.get("question", "") or p.get("title", "")
            if not p_q:
                continue
            if not _topics_compatible(kalshi_title, p_q):
                continue

            p_id = p.get("id", "")
            sem_score = semantic_map.get(p_id, 0.0)
            combined = _match_score(kalshi_title, p_q, sem_score)

            if combined >= min_score and combined > best_score:
                best_score = combined
                best_match = p

        return best_match
    @staticmethod
    def _compute_net_edge(kalshi_yes_ask: float, poly_no_ask: float) -> float:
        gross = 1.00 - kalshi_yes_ask - poly_no_ask
        fee   = 0.07 * (1.00 - kalshi_yes_ask)  # Kalshi fee on YES win
        return round(gross - fee, 4)
