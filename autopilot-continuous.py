#!/usr/bin/env python3
"""
Autopilot Continuous — Runs forever, streams EVERYTHING to Discord.
Per-phase model switching. Rate limit with per-tool cooldowns.
Full cycle visibility: Bootstrap→Analyze→Plan→Execute→Test→Commit→Report
"""

import json, os, subprocess, time, threading, requests, re, sys
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

BASE      = Path.home() / "Aarav/Autopilot"
STATE     = BASE / ".state"
RESULTS   = BASE / "results"
LOGS      = BASE / "logs"

cfg       = json.loads((STATE / "config.json").read_text())
DISCORD   = cfg["discord_webhook"]
WORKDIR   = cfg["workdir"]
NGROK_TOK = cfg["ngrok_authtoken"]

# Rate limits: key = tool name, value = cooldown_minutes
RATE_LIMITS = {
    "agy":          { "cooldown": 30, "fails": 0, "locked_until": None },
    "copilot-gpt52":{ "cooldown": 5,  "fails": 0, "locked_until": None },
    "opencode":     { "cooldown": 0,  "fails": 0, "locked_until": None },
    "ngrok":        { "cooldown": 0,  "fails": 0, "locked_until": None },
    "gemini":       { "cooldown": 0,  "fails": 0, "locked_until": None },
}

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
        print(f"[discord] {e}", file=sys.stderr)

def post_phase_start(phase: str):
    post_to_discord(phase, f"▶️ Phase started", 0x5865F2, "🚀")

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
    post_to_discord("RATE_LIMIT", 
        f"🔒 **{tool}** locked for {cooldown}min\nUnlocks: {RATE_LIMITS[tool]['locked_until']}", 
        0xFEE75C, "⏱️")

def mark_available(tool: str):
    """Unlock tool."""
    RATE_LIMITS[tool]["locked_until"] = None
    RATE_LIMITS[tool]["fails"] = 0

# ── Phase Execution ─────────────────────────────────────────────────────────
def run_phase(phase: str, prompt: str) -> tuple[bool, str]:
    """
    Run a phase with appropriate model + streaming output to Discord.
    Returns (success: bool, output: str)
    """
    post_phase_start(phase)
    
    # All phases use the same hermes --profile autopilot-worker now
    # Model/provider are configured in the profile's config.yaml
    
    try:
        # Use hermes for ALL phases — agy needs a PTY which subprocess can't provide
        # The autopilot-worker profile has opencode-zen + deepseek-v4-flash-free configured
        cmd = [
            "hermes",
            "--profile", "autopilot-worker",
            "chat",
            "-q", prompt,
            "-t", "terminal,file,code_execution",
            "-Q"
        ]
        tool_key = "opencode"
        timeout = 600  # 10 min per phase — AI agents need time to think + execute tools
        
        # Check rate limit
        if not is_available(tool_key):
            post_phase_error(phase, f"**{tool_key}** is rate-limited")
            return False, ""
        
        # Run command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        output = result.stdout + result.stderr
        
        # Check for critical errors — scan output content for failure indicators
        # IMPORTANT: hermes chat -q returns exit code 0 even with API failures (404, 429 after 3 retries)
        # We must check output content for failure indicators
        error_found = False
        error_type = "Unknown error"
        
        # Check return code
        if result.returncode != 0:
            error_found = True
        
        # Error patterns to scan in output (content-based, catches exit-code=0 failures)
        error_patterns = [
            ("api call failed", "API call failed (hermes)"),
            ("http 404", "Model not found (404)"),
            ("http 429", "Rate limited (429)"),
            ("notfounderror", "Model not found"),
            ("ratelimiterror", "Rate limit error"),
            ("all retries exhausted", "API retries exhausted"),
            ("unknown option", "CLI flag not recognized"),
            ("flags provided but not defined", "Invalid CLI flag"),
            ("traceback", "Python exception"),
            ("error opening TTY", "TTY not available"),
            ("bubbletea.*tty", "TTY not available"),
            ("permission denied", "Permission denied"),
            ("no such device or address", "TTY not available"),
        ]
        
        for pattern, desc in error_patterns:
            if re.search(pattern, output, re.IGNORECASE):
                error_found = True
                error_type = desc
                break
        
        if error_found:
            
            # Log the full error for debugging
            error_log = LOGS / f"error_{phase}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            error_log.write_text(f"Phase: {phase}\nTool: {tool_key}\nError Type: {error_type}\n\n{output}")
            
            post_phase_error(phase, f"❌ {error_type}\\nCheck: {error_log.name}")
            return False, output[:500]
        
        # Check for rate limit patterns
        if any(p in output.lower() for p in 
               ["rate limit", "429", "quota exceeded", "too many requests"]):
            mark_locked(tool_key)
            post_phase_error(phase, f"Rate limited by {tool_key}")
            return False, output[:500]
        
        # Success
        post_phase_output(phase, output[:1500])
        post_phase_complete(phase, f"✓ {phase} complete")
        mark_available(tool_key)
        
        return True, output
        
    except subprocess.TimeoutExpired:
        post_phase_error(phase, f"Timeout ({timeout}s)")
        return False, ""
    except Exception as e:
        post_phase_error(phase, str(e))
        return False, ""

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
