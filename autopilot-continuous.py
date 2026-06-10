#!/usr/bin/env python3
"""
Autopilot Continuous — Runs forever, streams EVERYTHING to Discord.
Per-phase model switching. Rate limit with per-tool cooldowns.
Full cycle visibility: Bootstrap→Analyze→Plan→Execute→Test→Commit→Report
"""

import json
import subprocess
import time
import requests
import re
import logging
from datetime import datetime, timedelta
from pathlib import Path

BASE      = Path.home() / "Aarav/Autopilot"
STATE     = BASE / ".state"
RESULTS   = BASE / "results"
LOGS      = BASE / "logs"

try:
    cfg       = json.loads((STATE / "config.json").read_text())
except (FileNotFoundError, json.JSONDecodeError) as e:
    msg = f"FATAL: Cannot load config from {STATE / 'config.json'}: {e}\n"
    msg += "Create a valid config.json in .state/ directory or restore from backup."
    print(msg, flush=True)
    with open(STATE / "config.json", "w") as f:
        json.dump({"discord_webhook": "", "workdir": str(BASE), "ngrok_authtoken": ""}, f, indent=2)
    cfg = json.loads((STATE / "config.json").read_text())

DISCORD   = cfg["discord_webhook"]
WORKDIR   = cfg["workdir"]
NGROK_TOK = cfg["ngrok_authtoken"]

# Persisted rate limits file
STATE_RATE_FILE = STATE / "rate_limits.json"

DEFAULT_RATE_LIMITS = {
    "agy":          { "cooldown": 30, "fails": 0, "locked_until": None },
    "copilot-gpt52":{ "cooldown": 5,  "fails": 0, "locked_until": None },
    "opencode":     { "cooldown": 0,  "fails": 0, "locked_until": None },
    "ngrok":        { "cooldown": 0,  "fails": 0, "locked_until": None },
}

def _load_rate_limits() -> dict:
    """Load rate limits from disk or return defaults."""
    try:
        data = json.loads(STATE_RATE_FILE.read_text())
        # Merge with defaults to pick up new entries
        for k, v in DEFAULT_RATE_LIMITS.items():
            if k not in data:
                data[k] = v
        return data
    except (FileNotFoundError, json.JSONDecodeError):
        return dict(DEFAULT_RATE_LIMITS)

def _save_rate_limits(data: dict):
    """Persist rate limits to disk."""
    STATE_RATE_FILE.write_text(json.dumps(data, indent=2))

# Load persisted state, then keep in-memory for hot access
RATE_LIMITS = _load_rate_limits()

PHASE_MODELS = [
    "bootstrap",
    "analyze",
    "plan",
    "execute",
    "test",
    "commit",
    "report",
]

# ── Discord Streaming ────────────────────────────────────────────────────────
def post_to_discord(phase: str, content: str, color: int = 0x5865F2, emoji: str = ""):
    """Stream phase output to Discord in real-time."""
    try:
        title = f"{emoji} {phase.upper()}"
        desc = content[:2000]  # Discord limit

        requests.post(DISCORD, json={
            "embeds": [{
                "title": title,
                "description": f"```\n{desc}\n```",
                "color": color,
                "timestamp": datetime.now(datetime.UTC).isoformat()
            }]
        }, timeout=5)
        time.sleep(0.3)  # rate limit: 1 msg per 0.3s
    except Exception as e:
        logging.error(f"Discord webhook error: {e}")

def post_phase_start(phase: str):
    post_to_discord(phase, "▶️ Phase started", 0x5865F2, "🚀")

def post_phase_output(phase: str, output: str):
    post_to_discord(phase, output, 0x3BA55C, "📝")

def post_phase_error(phase: str, error: str):
    post_to_discord(phase, f"❌ Error:\n{error}", 0xED4245, "⚠️")

def post_phase_complete(phase: str, status: str):
    color = 0x57F287 if "success" in status.lower() else 0xFEE75C
    emoji = "✅" if "success" in status.lower() else "⚠️"
    post_to_discord(phase, status, color, emoji)

# ── Rate Limiting ────────────────────────────────────────────────────────────
def is_available(tool: str) -> bool:
    """Check if tool is available (not in cooldown)."""
    if tool not in RATE_LIMITS:
        return True

    locked = RATE_LIMITS[tool]["locked_until"]
    if locked is None:
        return True

    return datetime.now() > datetime.fromisoformat(locked)

def mark_locked(tool: str):
    """Lock tool for cooldown period."""
    cooldown = RATE_LIMITS[tool]["cooldown"]
    RATE_LIMITS[tool]["locked_until"] = (
        datetime.now() + timedelta(minutes=cooldown)
    ).isoformat()
    RATE_LIMITS[tool]["fails"] += 1
    _save_rate_limits(RATE_LIMITS)
    post_to_discord("RATE_LIMIT",
        f"🔒 **{tool}** locked for {cooldown}min\nUnlocks: {RATE_LIMITS[tool]['locked_until']}",
        0xFEE75C, "⏱️")

def mark_available(tool: str):
    """Unlock tool."""
    RATE_LIMITS[tool]["locked_until"] = None
    RATE_LIMITS[tool]["fails"] = 0
    _save_rate_limits(RATE_LIMITS)

# ── Fallback chain: order of model providers to try ──────────────────────
FALLBACK_CHAIN = [
    {"tool_key": "opencode", "cmd": lambda p: [
        "hermes", "--profile", "autopilot-worker",
        "chat", "-q", p,
        "-t", "terminal,file,code_execution", "-Q"
    ]},
    {"tool_key": "ollama", "cmd": lambda p: [
        "ollama", "run", "llama3.2:1b", p
    ]},
]

# ── Phase Execution ─────────────────────────────────────────────────────────
def _execute_with_tool(phase: str, prompt: str, tool_key: str, cmd_builder) -> tuple[bool, str, str]:
    """Execute one phase attempt with a specific tool. Returns (success, output, error_type)."""
    timeout = 600 if tool_key == "opencode" else 120

    if not is_available(tool_key):
        return False, "", f"{tool_key} is rate-limited"

    cmd = cmd_builder(prompt)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, "", f"Timeout ({timeout}s)"
    except FileNotFoundError:
        return False, "", f"{tool_key} not found in PATH"
    except Exception as e:
        return False, "", str(e)

    output = result.stdout + result.stderr

    # Check return code
    if result.returncode != 0:
        return False, output[:500], f"Exit code {result.returncode}"

    # Content-based failure patterns
    error_patterns = [
        ("api call failed", "API call failed"),
        ("http 404", "Model not found (404)"),
        ("http 429", "Rate limited (429)"),
        ("http 500", "Server error (500)"),
        ("notfounderror", "Model not found"),
        ("ratelimiterror", "Rate limit error"),
        ("all retries exhausted", "API retries exhausted"),
        ("traceback", "Python exception"),
        ("error opening TTY", "TTY not available"),
        ("permission denied", "Permission denied"),
        ("no such device or address", "TTY not available"),
    ]
    for pattern, desc in error_patterns:
        if re.search(pattern, output, re.IGNORECASE):
            return False, output[:500], desc

    # Rate-limit indicators
    if any(p in output.lower() for p in
           ["rate limit", "429", "quota exceeded", "too many requests"]):
        mark_locked(tool_key)
        return False, output[:500], f"Rate limited by {tool_key}"

    # Check for empty/minimal response from ollama/local
    if tool_key == "ollama" and len(output.strip()) < 10:
        return False, output[:500], "Empty response from ollama"

    return True, output, ""


def run_phase(phase: str, prompt: str) -> tuple[bool, str]:
    """
    Run a phase with fallback model chain + streaming output to Discord.
    Tries: opencode-zen → ollama (llama3.2:1b)
    Returns (success: bool, output: str)
    """
    post_phase_start(phase)

    last_error = ""
    for entry in FALLBACK_CHAIN:
        tool_key = entry["tool_key"]
        cmd_builder = entry["cmd"]

        success, output, error_type = _execute_with_tool(phase, prompt, tool_key, cmd_builder)

        if success:
            post_phase_output(phase, output[:1500])
            post_phase_complete(phase, f"✓ {phase} complete (via {tool_key})")
            mark_available(tool_key)
            return True, output

        # Log failure for this tool
        error_log = LOGS / f"error_{phase}_{tool_key}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        error_log.write_text(f"Phase: {phase}\nTool: {tool_key}\nError: {error_type}\n\n{output}")
        post_phase_error(phase, f"⚠️ {tool_key} failed: {error_type} — trying next fallback")
        last_error = f"{tool_key}: {error_type}"

        # Brief pause between fallback attempts
        time.sleep(3)

    # All fallbacks exhausted
    post_phase_error(phase, f"❌ All fallbacks exhausted for phase '{phase}': {last_error}")
    return False, f"All fallbacks exhausted: {last_error}"

# ── Full Cycle ──────────────────────────────────────────────────────────────
def run_cycle(cycle_num: int):
    """Run one full improvement cycle with full Discord streaming."""

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    cycle_log = {
        "cycle": cycle_num,
        "timestamp": ts,
        "phases": {}
    }

    post_to_discord("CYCLE_START",
        f"🔄 **Cycle #{cycle_num}** started at {ts}",
        0x5865F2, "🚀")

    phases = [
        ("bootstrap", "Check codebase health and environment setup"),
        ("analyze", "Analyze codebase for issues, TODOs, failing tests"),
        ("plan", "Generate improvement tasks (max 10)"),
        ("execute", "Execute top 3 tasks using best available tool"),
        ("test", "Run test suite and verify fixes"),
        ("commit", "Commit changes with auto-generated messages"),
        ("report", "Generate final cycle report"),
    ]

    for phase, prompt in phases:
        success, output = run_phase(phase, prompt)
        cycle_log["phases"][phase] = {
            "success": success,
            "output": output[:500]
        }

        # Brief pause between phases
        time.sleep(2)

    # Final summary
    summary = "\n".join([
        f"• {p}: {'✅' if cycle_log['phases'].get(p, {}).get('success') else '❌'}"
        for p in PHASE_MODELS
    ])

    post_to_discord("CYCLE_COMPLETE",
        f"**Cycle #{cycle_num}** Summary:\n{summary}",
        0x57F287, "✅")

    # Save log
    (LOGS / f"cycle_{ts}.json").write_text(json.dumps(cycle_log, indent=2))
    return cycle_log

# ── Git Commit Tracking ──────────────────────────────────────────────────────
def get_git_commit_info() -> str:
    """Get git commit info: total commits, recent commits, branches, and stats."""
    try:
        # Get total commits
        total = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            capture_output=True, text=True, cwd=WORKDIR, timeout=10
        ).stdout.strip()

        # Get recent 5 commits with shortened hashes
        recent = subprocess.run(
            ["git", "log", "-5", "--oneline"],
            capture_output=True, text=True, cwd=WORKDIR, timeout=10
        ).stdout.strip()

        # Get current branch
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, cwd=WORKDIR, timeout=10
        ).stdout.strip()

        # Get commits ahead of origin
        ahead = subprocess.run(
            ["git", "rev-list", "--count", "origin/main..HEAD"],
            capture_output=True, text=True, cwd=WORKDIR, timeout=10
        ).stdout.strip()

        # Get last commit author
        author = subprocess.run(
            ["git", "log", "-1", "--pretty=format:%an"],
            capture_output=True, text=True, cwd=WORKDIR, timeout=10
        ).stdout.strip()

        report = f"""
Total Commits: **{total}**
Current Branch: **{branch}**
Commits Ahead of origin/main: **{ahead}**
Last Commit Author: **{author}**

**Recent Commits:**
```
{recent}
```
"""
        return report.strip()
    except Exception as e:
        return f"Error fetching git info: {str(e)[:200]}"

# ── Main Loop ────────────────────────────────────────────────────────────────
def main():
    post_to_discord("STARTUP",
        "🤖 **Autopilot Continuous** started\n"
        "Streaming all phase output to Discord\n"
        "Model switching per phase\n"
        "Rate limits: agy(30m), copilot-gpt52(5m), others(0m)",
        0x5865F2, "⚙️")

    cycle_num = 1
    last_git_report = datetime.now()  # Track last git commit info report

    while True:
        try:
            run_cycle(cycle_num)
            cycle_num += 1

            # Check if 24 hours have passed for git commit info report
            if (datetime.now() - last_git_report).total_seconds() >= 86400:  # 24 hours
                git_report = get_git_commit_info()
                post_to_discord("GIT_STATUS",
                    f"📊 **Git Commit Info (24h Report)**\\n{git_report}",
                    0xFFA500, "📈")
                last_git_report = datetime.now()

            # Wait before next cycle (configurable: 30 min default)
            post_to_discord("CYCLE_SLEEP",
                "💤 Waiting 30 minutes before next cycle...",
                0x5865F2, "⏱️")
            time.sleep(1800)  # 30 minutes

        except KeyboardInterrupt:
            post_to_discord("SHUTDOWN",
                "🛑 Autopilot stopped by user",
                0xED4245, "🛑")
            break
        except Exception as e:
            post_to_discord("ERROR",
                f"💥 Main loop error:\n{str(e)[:500]}",
                0xED4245, "⚠️")
            time.sleep(60)

if __name__ == "__main__":
    main()
