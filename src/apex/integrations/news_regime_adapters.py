from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from apex.core.logging import get_logger
from apex.integrations.daily_stock_analysis_adapter import DailyStockAnalysisAdapter  # noqa: F401

LOGGER = get_logger(__name__)


@dataclass
class MiroFishAdapter:
    repo_path: str
    _available: bool = field(default=False, init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.repo_path:
            LOGGER.warning("MiroFish repo path not configured")
            return
        candidate = Path(self.repo_path).expanduser().resolve()
        if not candidate.exists():
            LOGGER.warning("MiroFish repo not found at %s", candidate)
            return
        self._repo_root = candidate
        self._available = True
        LOGGER.info("MiroFish adapter initialized from %s", candidate)

    @property
    def available(self) -> bool:
        return self._available

    def get_overnight_digest(self, date: str | None = None) -> dict[str, Any]:
        if not self._available:
            return self._mock_digest()

        main_script = self._find_main_script()
        if not main_script:
            return self._mock_digest()

        try:
            cmd = [sys.executable, str(main_script)]
            if date:
                cmd.extend(["--date", date])

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode == 0 and result.stdout:
                return self._parse_digest_output(result.stdout)
        except Exception as exc:
            LOGGER.debug("MiroFish digest failed: %s", exc)

        return self._mock_digest()

    def _find_main_script(self) -> Path | None:
        for name in ["mirofish.py", "main.py", "run.py", "news_digest.py"]:
            path = self._repo_root / name
            if path.exists():
                return path
        for py_file in self._repo_root.rglob("*.py"):
            if py_file.name not in ["__init__.py", "setup.py"]:
                return py_file
        return None

    def _parse_digest_output(self, output: str) -> dict[str, Any]:
        return {
            "headlines": [],
            "sentiment": "neutral",
            "key_themes": [],
            "raw_output": output[:2000],
            "source": "mirofish",
        }

    def _mock_digest(self) -> dict[str, Any]:
        return {
            "headlines": [],
            "sentiment": "neutral",
            "key_themes": [],
            "source": "mirofish_mock",
            "note": "MiroFish not fully integrated - using stub",
        }


@dataclass
class KronosAdapter:
    repo_path: str
    _available: bool = field(default=False, init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.repo_path:
            LOGGER.warning("Kronos repo path not configured")
            return
        candidate = Path(self.repo_path).expanduser().resolve()
        if not candidate.exists():
            LOGGER.warning("Kronos repo not found at %s", candidate)
            return
        self._repo_root = candidate
        self._available = True
        LOGGER.info("Kronos adapter initialized from %s", candidate)

    @property
    def available(self) -> bool:
        return self._available

    def get_regime_classification(
        self,
        lookback_days: int = 30,
        symbols: list[str] | None = None,
    ) -> dict[str, Any]:
        if not self._available:
            return self._estimate_regime_from_market_data(symbols or ["SPY"])

        try:
            main_script = self._find_main_script()
            if main_script:
                cmd = [
                    sys.executable,
                    str(main_script),
                    "--regime",
                    "--days",
                    str(lookback_days),
                ]
                if symbols:
                    cmd.extend(["--symbols", ",".join(symbols)])

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                if result.returncode == 0 and result.stdout:
                    return self._parse_regime(result.stdout)
        except Exception as exc:
            LOGGER.debug("Kronos regime analysis failed: %s", exc)

        return self._estimate_regime_from_market_data(symbols or ["SPY"])

    def _find_main_script(self) -> Path | None:
        for name in ["kronos.py", "classify.py", "regime.py"]:
            path = self._repo_root / name
            if path.exists():
                return path
        for root, _, files in self._repo_root.rglob("*"):
            for f in files:
                if "classify" in f.lower() or "regime" in f.lower():
                    return Path(root) / f
        return None

    def _estimate_regime_from_market_data(self, symbols: list[str]) -> dict[str, Any]:
        import yfinance as yf

        try:
            spy = yf.Ticker("SPY").history(period="30d")
            if len(spy) < 5:
                return {
                    "regime": "unknown",
                    "confidence": 0.0,
                    "source": "insufficient_data",
                }

            returns = spy["Close"].pct_change().dropna()
            volatility = returns.std() * (252**0.5)
            trend = (spy["Close"].iloc[-1] / spy["Close"].iloc[0]) - 1

            sma_20 = spy["Close"].rolling(20).mean()
            above_sma = (
                spy["Close"].iloc[-1] > sma_20.iloc[-1] if len(sma_20) > 0 else True
            )

            high_vol = volatility > 0.20
            strong_trend = abs(trend) > 0.05
            bull = trend > 0 and above_sma
            bear = trend < 0 and not above_sma

            if high_vol and bull:
                regime = "high_vol_bull"
            elif high_vol and bear:
                regime = "high_vol_bear"
            elif not high_vol and bull:
                regime = "low_vol_bull"
            elif not high_vol and bear:
                regime = "low_vol_bear"
            elif not high_vol and not strong_trend:
                regime = "range_bound"
            else:
                regime = "unknown"

            return {
                "regime": regime,
                "volatility": volatility,
                "trend_pct": trend,
                "above_sma20": above_sma,
                "confidence": 0.7,
                "source": "yfinance_estimation",
            }
        except Exception:
            return {"regime": "unknown", "confidence": 0.0, "source": "exception"}

    def _parse_regime(self, output: str) -> dict[str, Any]:
        output_lower = output.lower()
        regimes = [
            "trending",
            "range_bound",
            "high_vol",
            "low_vol",
            "bullish",
            "bearish",
            "neutral",
        ]
        detected = [r for r in regimes if r in output_lower]
        return {
            "regime": detected[0] if detected else "unknown",
            "raw_output": output[:1000],
            "source": "kronos",
        }
