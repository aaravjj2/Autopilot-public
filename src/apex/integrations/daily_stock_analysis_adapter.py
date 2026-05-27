from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from apex.core.config import Settings
from apex.core.logging import get_logger

LOGGER = get_logger(__name__)


def _has_llm_keys_for_dsa(env: dict[str, str]) -> bool:
    keys = (
        "GEMINI_API_KEY",
        "GEMINI_API_KEYS",
        "OPENAI_API_KEY",
        "DEEPSEEK_API_KEY",
        "AIHUBMIX_KEY",
        "ANSPIRE_API_KEYS",
        "GROQ_API_KEY",
    )
    if any((env.get(k) or "").strip() for k in keys):
        return True
    if (env.get("LLM_PROVIDER") or "").lower() == "ollama":
        return bool((env.get("OLLAMA_HOST") or "http://localhost:11434").strip())
    return False


@dataclass
class DailyStockAnalysisAdapter:
    """
    Runs ZhuLinsen/daily_stock_analysis as a subprocess with APEX-friendly flags.

    Primary mode: US market review (--market-review) written to reports/market_review_*.md
    Optional: per-stock digest for a capped watchlist (--stocks, requires LLM keys in env).
    """

    repo_path: str
    settings: Settings | None = None
    _available: bool = field(default=False, init=False, repr=False)
    _repo_root: Path = field(default_factory=Path, init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.repo_path:
            LOGGER.warning("daily_stock_analysis repo path not configured")
            return
        candidate = Path(self.repo_path).expanduser().resolve()
        main_py = candidate / "main.py"
        if not main_py.is_file():
            LOGGER.warning("daily_stock_analysis main.py not found at %s", candidate)
            return
        self._repo_root = candidate
        self._available = True
        LOGGER.info("DailyStockAnalysis adapter initialized from %s", candidate)

    @property
    def available(self) -> bool:
        if not self._available:
            return False
        if self.settings is not None and not self.settings.daily_stock_analysis_enabled:
            return False
        return True

    def _reports_dir(self) -> Path:
        return self._repo_root / "reports"

    def _build_dsa_env(self, symbols: list[str] | None) -> dict[str, str]:
        env = os.environ.copy()
        s = self.settings
        region = (s.daily_stock_analysis_region if s else "us") or "us"
        env["MARKET_REVIEW_REGION"] = region
        env["REPORT_LANGUAGE"] = "en"
        env["MARKET_REVIEW_ENABLED"] = "true"
        env["RUN_IMMEDIATELY"] = "false"
        env["TRADING_DAY_CHECK_ENABLED"] = "false"
        env["SCHEDULE_ENABLED"] = "false"
        if symbols:
            env["STOCK_LIST"] = ",".join(symbols)
        apex_env = Path(__file__).resolve().parents[3] / ".env"
        if apex_env.is_file():
            env["ENV_FILE"] = str(apex_env)
        if s:
            prov = (s.llm_provider or "openai").lower()
            env["LLM_PROVIDER"] = prov
            if prov == "groq" and os.environ.get("GROQ_API_KEY"):
                env["OPENAI_API_KEY"] = os.environ["GROQ_API_KEY"]
                env["OPENAI_BASE_URL"] = s.llm_backend_url or "https://api.groq.com/openai/v1"
                env["OPENAI_MODEL"] = s.llm_model
            elif prov == "ollama":
                env["OLLAMA_HOST"] = s.ollama_host
                env["OLLAMA_MODEL"] = s.ollama_model or s.llm_model
        return env

    def _run_main(self, cli_args: list[str], timeout_sec: int) -> subprocess.CompletedProcess[str]:
        cmd = [sys.executable, str(self._repo_root / "main.py"), *cli_args]
        env = self._build_dsa_env(None)
        LOGGER.info("DailyStockAnalysis: %s", " ".join(cli_args[:6]))
        return subprocess.run(
            cmd,
            cwd=str(self._repo_root),
            env=env,
            capture_output=True,
            text=True,
            timeout=max(30, timeout_sec),
        )

    def _read_latest_report(self, pattern: str) -> str:
        reports = self._reports_dir()
        if not reports.is_dir():
            return ""
        files = sorted(reports.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
        if not files:
            return ""
        try:
            return files[0].read_text(encoding="utf-8", errors="replace").strip()
        except OSError as exc:
            LOGGER.warning("Could not read DSA report %s: %s", files[0], exc)
            return ""

    def _run_market_review(self) -> str:
        s = self.settings
        timeout = int(s.daily_stock_analysis_timeout_market_sec) if s else 300
        proc = self._run_main(
            ["--market-review", "--no-notify", "--force-run"],
            timeout_sec=timeout,
        )
        if proc.returncode != 0:
            LOGGER.warning(
                "DSA market-review exit %s stderr=%s",
                proc.returncode,
                (proc.stderr or "")[:500],
            )
        text = self._read_latest_report("market_review_*.md")
        if not text and proc.stdout:
            text = proc.stdout.strip()
        return text

    def _run_stock_digest(self, symbols: list[str]) -> str:
        if not symbols:
            return ""
        s = self.settings
        if s is None or not s.daily_stock_analysis_stock_digest:
            return ""
        env = self._build_dsa_env(symbols)
        if not _has_llm_keys_for_dsa(env):
            LOGGER.info(
                "DSA stock digest skipped: no LLM API keys in environment (needs GEMINI/OPENAI/GROQ/etc.)"
            )
            return ""
        cap = max(1, min(len(symbols), int(s.daily_stock_analysis_max_stocks)))
        batch = symbols[:cap]
        timeout = int(s.daily_stock_analysis_timeout_stocks_sec)
        proc = subprocess.run(
            [
                sys.executable,
                str(self._repo_root / "main.py"),
                "--stocks",
                ",".join(batch),
                "--no-notify",
                "--force-run",
                "--no-market-review",
            ],
            cwd=str(self._repo_root),
            env=env,
            capture_output=True,
            text=True,
            timeout=max(60, timeout),
        )
        if proc.returncode != 0:
            LOGGER.warning(
                "DSA stock digest exit %s stderr=%s",
                proc.returncode,
                (proc.stderr or "")[:500],
            )
        today = date.today().strftime("%Y%m%d")
        text = self._read_latest_report(f"report_{today}.md")
        if not text:
            text = self._read_latest_report("report_*.md")
        return text

    def get_daily_market_report(
        self,
        symbols: list[str] | None = None,
        run_date: str | None = None,
    ) -> dict[str, Any]:
        _ = run_date
        if not self.available:
            return self._empty_report("adapter_unavailable")

        s = self.settings
        segments: list[str] = []
        market_md = ""
        stock_md = ""

        if s is None or s.daily_stock_analysis_market_review:
            market_md = self._run_market_review()
            if market_md:
                segments.append(f"## US market review (daily_stock_analysis)\n\n{market_md}")

        if symbols:
            stock_md = self._run_stock_digest(symbols)
            if stock_md:
                segments.append(
                    f"## Watchlist digest ({len(symbols[: s.daily_stock_analysis_max_stocks])} symbols)\n\n{stock_md}"
                )

        combined = "\n\n".join(segments).strip()
        if not combined:
            return self._empty_report("no_report_output")

        regime = "unknown"
        lower = combined.lower()
        if "bull" in lower or "上涨" in combined:
            regime = "risk_on"
        elif "bear" in lower or "下跌" in combined:
            regime = "risk_off"

        return {
            "market_overview": {"region": s.daily_stock_analysis_region if s else "us"},
            "sectors": [],
            "key_levels": {},
            "regime": regime,
            "raw_report": combined[:12000],
            "market_review_md": market_md[:8000] if market_md else "",
            "stock_digest_md": stock_md[:8000] if stock_md else "",
            "symbols_requested": list(symbols or [])[: (s.daily_stock_analysis_max_stocks if s else 8)],
            "source": "daily_stock_analysis",
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        }

    def _empty_report(self, reason: str) -> dict[str, Any]:
        return {
            "market_overview": {},
            "sectors": [],
            "key_levels": {},
            "regime": "unknown",
            "raw_report": "",
            "source": "daily_stock_analysis_unavailable",
            "note": reason,
        }
