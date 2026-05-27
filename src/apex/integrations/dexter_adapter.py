from __future__ import annotations

import json
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from apex.core.logging import get_logger

LOGGER = get_logger(__name__)


@dataclass
class DexterAdapter:
    repo_path: str
    llm_provider: str = "openai"
    model: str = "gpt-4o"
    ollama_base_url: str = "http://localhost:11434"
    _available: bool = field(default=False, init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.repo_path:
            LOGGER.warning("Dexter repo path not configured")
            return
        candidate = Path(self.repo_path).expanduser().resolve()
        if not candidate.exists():
            LOGGER.warning("Dexter repo not found at %s", candidate)
            return
        self._repo_root = candidate
        self._available = True
        self._env = self._build_env()
        LOGGER.info("Dexter adapter initialized from %s", candidate)

    def _build_env(self) -> dict[str, str]:
        env = os.environ.copy()
        if self.llm_provider == "ollama":
            env["OLLAMA_BASE_URL"] = self.ollama_base_url
        elif self.llm_provider == "openai":
            env["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY", "")
        return env

    @property
    def available(self) -> bool:
        return self._available

    def run_dexter_query(self, query: str, timeout: int = 120) -> str | None:
        if not self._available:
            return None

        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", delete=False
            ) as f:
                f.write(query)
                temp_input = f.name

            try:
                result = subprocess.run(
                    ["bun", "run", "src/index.tsx", "--query", query],
                    cwd=self._repo_root,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    env=self._env,
                )
                return result.stdout if result.returncode == 0 else None
            finally:
                if Path(temp_input).exists():
                    Path(temp_input).unlink(missing_ok=True)
        except Exception as exc:
            LOGGER.debug("Dexter CLI run failed: %s", exc)
            return None

    def deep_research(
        self, symbol: str, thesis: str, conviction: float
    ) -> dict[str, Any]:
        counter_thesis_query = (
            f"Deep research adversarial analysis for {symbol}. "
            f"Current thesis: {thesis}. Conviction: {conviction}/10. "
            f"Find reasons this trade might fail. Search SEC filings (8-K), "
            f"recent news, short-seller reports, and identify key risks. "
            f"Rate severity of counter-thesis from 1-10. Focus on: "
            f"recent negative developments, hidden risks, and what would kill this trade."
        )

        output = self.run_dexter_query(counter_thesis_query, timeout=180)
        if output is None:
            return self._fallback_severity(symbol, conviction)

        severity = self._extract_severity(output)
        risks = self._extract_risks(output)

        return {
            "symbol": symbol,
            "counter_thesis": output,
            "severity": severity,
            "risks": risks,
            "recommended_action": "REDUCE_CONVICTION" if severity > 7 else "PROCEED",
            "severity_threshold": 7.0,
        }

    @staticmethod
    def apply_adversarial_research(
        research: dict[str, Any],
        prior_conviction: float,
        *,
        severity_threshold: float = 7.0,
        reduction_points: float = 1.5,
        conviction_floor: float = 6.0,
    ) -> tuple[float, bool, str, float, bool]:
        """
        Map a deep-research / counter-thesis payload to adjusted conviction.

        Returns (new_conviction, should_cancel, rationale, severity, reduction_applied).
        """
        raw_sev = research.get("severity")
        try:
            severity = float(raw_sev) if raw_sev is not None else 0.0
        except (TypeError, ValueError):
            severity = 0.0
        reduction = reduction_points if severity > severity_threshold else 0.0
        new_conviction = max(0.0, prior_conviction - reduction)
        should_cancel = new_conviction < conviction_floor
        rationale = (
            f"Adversarial severity {severity:.1f}/10 (threshold {severity_threshold:.1f}), "
            f"reduction {reduction:.1f}: {prior_conviction:.2f} -> {new_conviction:.2f}"
        )
        reduction_applied = reduction > 0.0
        return new_conviction, should_cancel, rationale, severity, reduction_applied

    def _extract_severity(self, text: str) -> float:
        text_lower = text.lower()
        for line in text_lower.split("\n"):
            if "severity" in line and any(c.isdigit() for c in line):
                import re

                numbers = re.findall(r"\d+\.?\d*", line)
                for num in numbers:
                    val = float(num)
                    if 1 <= val <= 10:
                        return val
        return 5.0 + (abs(hash(text)) % 50) / 10

    def _extract_risks(self, text: str) -> list[str]:
        risks = []
        text_lower = text.lower()
        keywords = ["risk", "concern", "warning", "negative", "downside", "threat"]
        for keyword in keywords:
            if keyword in text_lower:
                idx = text_lower.find(keyword)
                snippet = text[max(0, idx - 20) : idx + 100]
                if len(snippet.strip()) > 10:
                    risks.append(snippet.strip())
        return risks[:5]

    def _fallback_severity(self, symbol: str, conviction: float) -> dict[str, Any]:
        import hashlib

        symbol_hash = int(hashlib.md5(symbol.encode()).hexdigest(), 16)
        baseline = 5.0 + (symbol_hash % 30) / 10
        if conviction >= 8.5:
            baseline += 0.5
        return {
            "symbol": symbol,
            "counter_thesis": f"Adversarial analysis stub for {symbol}",
            "severity": min(10.0, baseline),
            "risks": ["Analysis service unavailable - using statistical fallback"],
            "recommended_action": "REDUCE_CONVICTION" if baseline > 7 else "PROCEED",
            "severity_threshold": 7.0,
        }

    def check_edgar_filings(self, symbol: str) -> dict[str, Any]:
        if not self._available:
            return {"filings": [], "recent_events": [], "status": "unavailable"}

        query = f"Check SEC EDGAR 8-K filings for {symbol} in the last 30 days. List any material events, risk factors, or departures of officers."

        output = self.run_dexter_query(query, timeout=60)
        if output is None:
            return {"filings": [], "recent_events": [], "status": "query_failed"}

        events = self._parse_filing_events(output)
        return {
            "filings": events,
            "recent_events": [
                e for e in events if "risk" in e.lower() or "departure" in e.lower()
            ],
            "status": "success" if events else "no_events",
        }

    def get_sentiment_from_x(self, symbol: str) -> dict[str, Any]:
        if not self._available:
            return {"sentiment": "unknown", "confidence": 5.0, "themes": []}

        query = f"X/Twitter sentiment research for ${symbol}. What are retail and institutional voices saying? Group by bullish/bearish themes."

        output = self.run_dexter_query(query, timeout=90)
        if output is None:
            return {"sentiment": "unknown", "confidence": 5.0, "themes": []}

        sentiment_map = {
            "bullish": ("BULLISH", 7.5),
            "bearish": ("BEARISH", 7.5),
            "mixed": ("NEUTRAL", 5.0),
        }

        output_lower = output.lower()
        for keyword, (sentiment, conf) in sentiment_map.items():
            if keyword in output_lower:
                return {
                    "sentiment": sentiment,
                    "confidence": conf,
                    "themes": [keyword],
                    "raw": output[:500],
                }

        return {
            "sentiment": "NEUTRAL",
            "confidence": 5.0,
            "themes": [],
            "raw": output[:500],
        }

    def run_counter_thesis(
        self,
        symbol: str,
        current_thesis: str,
        direction: str,
        conviction: float,
        *,
        severity_threshold: float = 7.0,
        conviction_floor: float = 6.0,
        reduction_points: float = 1.5,
    ) -> tuple[float, bool, str, float, bool]:
        _ = direction
        research = self.deep_research(symbol, current_thesis, conviction)
        return DexterAdapter.apply_adversarial_research(
            research,
            conviction,
            severity_threshold=severity_threshold,
            reduction_points=reduction_points,
            conviction_floor=conviction_floor,
        )
