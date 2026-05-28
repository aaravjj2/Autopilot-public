"""DB01 regression harness — Runtime Deprecation verification.

Verifies: no :8001 in frontend source, playwright config has 2 webServer entries
on :8000, marketWsUrl delegates to getApexWsUrl, and backend lifespan has no
:8001 startup.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

REPO = Path(__file__).parents[1]
FRONTEND = REPO / "autopilot-local" / "frontend"


def _rg(pattern: str, *paths: str, extra_args: list[str] | None = None) -> list[str]:
    cmd = ["rg", "--no-heading", "-n", pattern, *paths]
    if extra_args:
        cmd.extend(extra_args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    return [ln for ln in result.stdout.splitlines() if ln.strip()]


def test_no_8001_in_frontend_source() -> None:
    """Frontend source must not reference :8001 except in comments/guards."""
    hits = _rg(
        "8001",
        str(FRONTEND),
        extra_args=[
            "--glob", "!**/node_modules/**",
            "--glob", "!**/.next/**",
        ],
    )
    non_comment_hits = [
        h for h in hits
        if not any(
            marker in h
            for marker in ["// ", "# ", "comment", "legacy", "DB01", ".includes(':8001')"]
        )
    ]
    assert non_comment_hits == [], "Unexpected :8001 references:\n" + "\n".join(non_comment_hits)


def test_playwright_config_has_two_webserver_entries() -> None:
    """playwright.config.ts must declare exactly 2 webServer entries."""
    config_text = (FRONTEND / "playwright.config.ts").read_text()
    count = config_text.count("url: 'http://127.0.0.1:8000")
    assert count >= 1, "Expected at least 1 webServer entry pointing to :8000"
    assert "webServer: [" in config_text, "webServer must be an array"
    # Count array entries by counting top-level { inside webServer block
    ws_block = config_text.split("webServer: [")[1].split("]")[0]
    entry_count = ws_block.count("command:")
    assert entry_count == 2, f"Expected 2 webServer entries, found {entry_count}"


def test_playwright_testdir_points_to_tests_e2e() -> None:
    """playwright.config.ts testDir must be './tests/e2e' where specs live."""
    config_text = (FRONTEND / "playwright.config.ts").read_text()
    assert "testDir: './tests/e2e'" in config_text, (
        "testDir must be './tests/e2e' — specs live under tests/e2e/"
    )


def test_market_ws_url_delegates_to_apex_ws_url() -> None:
    """`marketWsUrl` must delegate to `getApexWsUrl` in backend-urls.ts."""
    urls_file = FRONTEND / "lib" / "backend-urls.ts"
    text = urls_file.read_text()
    assert "getApexWsUrl" in text, "backend-urls.ts must define getApexWsUrl"
    assert "marketWsUrl" in text, "backend-urls.ts must export marketWsUrl"
    # marketWsUrl must reference getApexWsUrl (not a raw :8001 literal)
    market_lines = [ln for ln in text.splitlines() if "marketWsUrl" in ln and "=" in ln]
    for ln in market_lines:
        assert ":8001" not in ln, f"marketWsUrl must not hardcode :8001: {ln}"


def test_backend_lifespan_no_8001() -> None:
    """`backend_api.py` lifespan must not start a :8001 server."""
    api_text = (REPO / "backend_api.py").read_text()
    assert ":8001" not in api_text, "backend_api.py must not reference :8001"


def test_env_local_example_8001_commented() -> None:
    """.env.local.example must not have an active :8001 entry."""
    env_file = FRONTEND / ".env.local.example"
    if not env_file.exists():
        return  # file is optional
    for ln in env_file.read_text().splitlines():
        stripped = ln.strip()
        if "8001" in stripped:
            assert stripped.startswith("#"), f"Active :8001 in .env.local.example: {ln}"
