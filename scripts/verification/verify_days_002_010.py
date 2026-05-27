#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

ROOT = Path("/home/aarav/Aarav/Autopilot")
PLAN_DIR = Path("/home/aarav/.cursor/plans/one-year-daily")
DEFAULT_LOG = ROOT / "logs/day_progress_days_001_011.md"


@dataclass
class CheckResult:
    name: str
    status: str
    evidence: str
    command: str | None = None
    retry_command: str | None = None


@dataclass
class DayResult:
    day: int
    deliverable: str
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def status(self) -> str:
        statuses = {c.status for c in self.checks}
        if "FAIL" in statuses:
            return "FAIL"
        if "BLOCKED" in statuses:
            return "BLOCKED"
        return "PASS"


def run_cmd(cmd: str) -> tuple[int, str, str]:
    proc = subprocess.run(cmd, shell=True, text=True, capture_output=True, cwd=ROOT)
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def classify_http_result(returncode: int, stdout: str, stderr: str) -> tuple[str, str]:
    if returncode == 0:
        try:
            payload = json.loads(stdout)
            if isinstance(payload, dict) and "status" in payload:
                return "PASS", f"status={payload.get('status')}"
            return "FAIL", "HTTP returned JSON but missing expected status field"
        except json.JSONDecodeError:
            return "FAIL", "HTTP succeeded but missing expected JSON body"
    if "Failed to connect" in stderr or "Connection refused" in stderr:
        return "BLOCKED", stderr or "service unavailable"
    return "FAIL", stderr or "health check command failed"


def classify_api_health_result(returncode: int, stdout: str, stderr: str) -> tuple[str, str]:
    if returncode != 0:
        if "Failed to connect" in stderr or "Connection refused" in stderr:
            return "BLOCKED", stderr or "service unavailable"
        return "FAIL", stderr or "api health command failed"
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return "FAIL", "HTTP succeeded but missing expected JSON body"
    if isinstance(payload, dict) and "engine" in payload and "alpaca" in payload:
        return "PASS", "contains engine + alpaca payload"
    return "FAIL", "missing expected fields engine/alpaca"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def extract_deliverable(day: int) -> str:
    text = read_text(PLAN_DIR / f"day-{day:03d}.md")
    for line in text.splitlines():
        if line.startswith("**Deliverable today:**"):
            return line.replace("**Deliverable today:**", "").strip()
    return "Deliverable not found in plan"


def check_file_exists(path: Path, label: str) -> CheckResult:
    if path.exists():
        return CheckResult(label, "PASS", f"found {path}")
    return CheckResult(label, "FAIL", f"missing {path}")


def file_contains_regex(path: Path, pattern: str, label: str, expect_found: bool) -> CheckResult:
    text = read_text(path)
    matched = re.search(pattern, text, re.MULTILINE) is not None
    if expect_found and matched:
        return CheckResult(label, "PASS", f"pattern found in {path}")
    if (not expect_found) and (not matched):
        return CheckResult(label, "PASS", f"pattern absent in {path}")
    return CheckResult(label, "FAIL", f"pattern expectation failed in {path}")


def global_checks() -> list[CheckResult]:
    checks: list[CheckResult] = []

    frontend_dir = ROOT / "autopilot-local/frontend"
    playwright_cfg = frontend_dir / "playwright.config.ts"
    ci_path = ROOT / ".github/workflows/ci.yml"
    page_path = frontend_dir / "app/page.tsx"
    package_json = ROOT / "autopilot-local/package.json"

    checks.append(
        file_contains_regex(
            playwright_cfg,
            r"testDir:\s*'./tests/e2e'",
            "Playwright test discovery is tests/e2e",
            expect_found=True,
        )
    )
    checks.append(
        file_contains_regex(
            playwright_cfg,
            r"backend_api:app --host 127\.0\.0\.1 --port 8000",
            "Playwright webServer uses backend :8000",
            expect_found=True,
        )
    )
    cmd_8001 = f"rg -n '8001' '{frontend_dir}'"
    code, out, _ = run_cmd(cmd_8001)
    if code == 0 and out:
        non_comment_hits = []
        for line in out.splitlines():
            line_no_prefix = line.split(":", 2)
            snippet = line_no_prefix[2].strip() if len(line_no_prefix) == 3 else line
            if (
                not snippet.startswith("//")
                and not snippet.startswith("*")
                and "legacy removed" not in snippet
                and "includes(':8001')" not in snippet
            ):
                non_comment_hits.append(line)
        if non_comment_hits:
            checks.append(
                CheckResult(
                    "Frontend :8001 removed from default path",
                    "FAIL",
                    non_comment_hits[0],
                    cmd_8001,
                )
            )
        else:
            checks.append(
                CheckResult(
                    "Frontend :8001 removed from default path",
                    "PASS",
                    "only comment/reference mentions found",
                    cmd_8001,
                )
            )
    else:
        checks.append(
            CheckResult("Frontend :8001 removed from default path", "PASS", "no 8001 matches", cmd_8001)
        )

    ci_text = read_text(ci_path)
    start_idx = ci_text.find("Start APEX backend for E2E")
    wait_idx = ci_text.find("Wait for APEX health")
    if 0 <= start_idx < wait_idx:
        checks.append(
            CheckResult(
                "CI starts backend before waiting health",
                "PASS",
                "workflow order is Start APEX backend -> Wait for APEX health",
            )
        )
    else:
        checks.append(
            CheckResult(
                "CI starts backend before waiting health",
                "FAIL",
                "workflow order invalid or missing health wait step",
            )
        )

    code, out, err = run_cmd("curl -sS -f http://127.0.0.1:8000/health")
    health_status, health_ev = classify_http_result(code, out, err)
    checks.append(
        CheckResult(
            "Backend /health responds",
            health_status,
            health_ev,
            "curl -sS -f http://127.0.0.1:8000/health",
            "cd /home/aarav/Aarav/Autopilot && PYTHONPATH=src python -m uvicorn backend_api:app --host 127.0.0.1 --port 8000",
        )
    )

    code, out, err = run_cmd("curl -sS -f http://127.0.0.1:8000/api/health")
    api_health_status, api_health_ev = classify_api_health_result(code, out, err)
    checks.append(
        CheckResult(
            "Backend /api/health responds",
            api_health_status,
            api_health_ev,
            "curl -sS -f http://127.0.0.1:8000/api/health",
            "cd /home/aarav/Aarav/Autopilot && PYTHONPATH=src python -m uvicorn backend_api:app --host 127.0.0.1 --port 8000",
        )
    )

    checks.append(
        file_contains_regex(
            page_path,
            r'href="\/dashboard"',
            "Frontend landing references /dashboard",
            expect_found=True,
        )
    )
    checks.append(
        file_contains_regex(
            package_json,
            r'"dev":\s*"concurrently -n apex,web',
            "Unified dev script references apex+web",
            expect_found=True,
        )
    )

    return checks


def day_specific_check(day: int) -> CheckResult:
    if day == 2:
        return check_file_exists(ROOT / "autopilot-local/.env.local.example", "Day 002 .env.local.example exists")
    if day == 3:
        p = ROOT / "docs/runtime/engine-singleton-audit.md"
        if not p.exists():
            return CheckResult("Day 003 singleton audit exists", "FAIL", f"missing {p}")
        return file_contains_regex(p, r"build_engine\(", "Day 003 audit references build_engine()", expect_found=True)
    if day == 4:
        return check_file_exists(ROOT / "docs/scheduler/job-registry.md", "Day 004 scheduler registry doc exists")
    if day == 5:
        return check_file_exists(ROOT / ".github/workflows/ci.yml", "Day 005 CI workflow exists")
    if day in {6, 8, 9, 10}:
        return check_file_exists(ROOT / "autopilot-local/start-unified.sh", f"Day {day:03d} start-unified.sh exists")
    if day == 7:
        return file_contains_regex(
            ROOT / "autopilot-local/package.json",
            r'"dev":\s*"concurrently -n apex,web -c blue,green',
            "Day 007 dev script is 2-process concurrently",
            expect_found=True,
        )
    return CheckResult(f"Day {day:03d} scoped check", "FAIL", "no day-specific check configured")


def verify_day(day: int, shared_checks: Sequence[CheckResult]) -> DayResult:
    result = DayResult(day=day, deliverable=extract_deliverable(day))
    result.checks.extend(shared_checks)
    result.checks.append(day_specific_check(day))
    return result


def render_console(results: Sequence[DayResult]) -> str:
    lines: list[str] = []
    for day in results:
        lines.append(f"DAY {day.day:03d}: {day.status} — {day.deliverable}")
        for c in day.checks:
            cmd = f" | cmd={c.command}" if c.command else ""
            retry = f" | retry={c.retry_command}" if c.status == "BLOCKED" and c.retry_command else ""
            lines.append(f"  - [{c.status}] {c.name}: {c.evidence}{cmd}{retry}")
    return "\n".join(lines)


def render_markdown(results: Sequence[DayResult]) -> str:
    now = datetime.now(timezone.utc).isoformat()
    lines = [
        "",
        "### Day 2-10 Verification Harness Results",
        "",
        f"- Timestamp: {now}",
        "- Runner: `python scripts/verification/verify_days_002_010.py --days 2-10`",
        "",
        "| Day | Status | Deliverable |",
        "|---|---|---|",
    ]
    for r in results:
        lines.append(f"| {r.day:03d} | {r.status} | {r.deliverable} |")
    lines.append("")
    lines.append("#### Evidence")
    for r in results:
        lines.append(f"- Day {r.day:03d} ({r.status})")
        for c in r.checks:
            cmd = f" | cmd: `{c.command}`" if c.command else ""
            lines.append(f"  - [{c.status}] {c.name}: {c.evidence}{cmd}")
            if c.status == "BLOCKED" and c.retry_command:
                lines.append(f"  - Retry: `{c.retry_command}`")
    lines.append("")
    return "\n".join(lines)


def parse_days(arg: str) -> list[int]:
    if "-" in arg:
        start, end = arg.split("-", maxsplit=1)
        return list(range(int(start), int(end) + 1))
    return [int(x.strip()) for x in arg.split(",") if x.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify day-002..day-010 objective checks")
    parser.add_argument("--days", default="2-10", help="Range/list like 2-10 or 2,3,4")
    parser.add_argument("--update-log", default=str(DEFAULT_LOG), help="Progress log markdown file path")
    parser.add_argument("--no-log-update", action="store_true", help="Skip writing progress log")
    args = parser.parse_args()

    days = parse_days(args.days)
    shared = global_checks()
    results = [verify_day(day, shared) for day in days]

    console = render_console(results)
    print(console)

    if not args.no_log_update:
        log_path = Path(args.update_log)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        existing = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
        log_path.write_text(existing + render_markdown(results), encoding="utf-8")
        print(f"\nUpdated log: {log_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
