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

PHASE_MODELS = {
    "bootstrap":  ("deepseek-v4-flash-free", "opencode-zen"),
    "analyze":    ("gpt-5.2-codex", "opencode-zen"),  # Changed from copilot to opencode-zen
    "plan":       ("deepseek-v4-flash-free", "opencode-zen"),
    "execute":    ("agy-switch", "hermes"),  # agy with model switching
    "test":       ("deepseek-v4-flash-free", "opencode-zen"),
    "commit":     ("deepseek-v4-flash-free", "opencode-zen"),
    "report":     ("gpt-5.2-codex", "opencode-zen"),  # Changed from copilot to opencode-zen
}

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
                "timestamp": datetime.utcnow().isoformat()
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
    
    model, provider = PHASE_MODELS.get(phase, ("deepseek-v4-flash-free", "opencode-zen"))
    
    try:
        if phase == "execute" and provider == "hermes":
            # Use agy with model switching
            cmd = [
                "agy",
                "--dangerously-skip-permissions",
                "--add-dir", WORKDIR,
                "--model", "gpt-5.2-codex",
                prompt
            ]
            tool_key = "agy"
            timeout = 600
        else:
            # Use cbm (codebuff-mod) for all other phases
            # cbm expects: cbm [options] [prompt...]
            # Working directory is set via --cwd, not changing subprocess cwd
            cmd = [
                "cbm",
                "--cwd", WORKDIR,
                prompt
            ]
            if provider == "hermes":
                tool_key = "agy"
                timeout = 600
            else:
                tool_key = provider if provider != "opencode-zen" else "opencode"
                timeout = 300
        
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
        
        # Check for critical errors
        if result.returncode != 0:
            error_patterns = {
                "unknown option": "CLI flag not recognized",
                "flags provided but not defined": "Invalid flag passed to tool",
                "traceback": "Python exception in tool",
                "not found": "Tool binary not found",
                "permission denied": "Permission error"
            }
            
            error_type = "Unknown error"
            for pattern, desc in error_patterns.items():
                if pattern in output.lower():
                    error_type = desc
                    break
            
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
        for p, _ in phases
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
