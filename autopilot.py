#!/usr/bin/env python3
"""
Autopilot — self-planning, multi-tool, multi-provider coding agent daemon.
Runs forever. Plans its own tasks. Routes to best available tool.
Reports everything to Discord.
"""

import json
import subprocess
import time
import threading
import requests
import re
from datetime import datetime, timedelta
from pathlib import Path

BASE      = Path.home() / "Aarav/Autopilot"
STATE     = BASE / ".state"
RESULTS   = BASE / "results"
LOGS      = BASE / "logs"
NOTEBOOKS = BASE / "notebooks"

cfg       = json.loads((STATE / "config.json").read_text())
DISCORD   = cfg["discord_webhook"]
WORKDIR   = cfg["workdir"]
NGROK_TOK = cfg["ngrok_authtoken"]
KAGGLE_UN = cfg["kaggle_username"]
OR_KEY    = cfg.get("openrouter_key", "")
OR_MODEL  = cfg.get("openrouter_free_model", "deepseek/deepseek-v4-flash:free")

# ── Discord ────────────────────────────────────────────────────────────
def disc(msg: str, color: int = 0x5865F2, title: str = "Autopilot"):
    try:
        requests.post(DISCORD, json={
            "embeds": [{
                "title": title,
                "description": msg[:4000],
                "color": color,
                "timestamp": datetime.utcnow().isoformat()
            }]
        }, timeout=5)
        time.sleep(0.5)   # stay under 30/min webhook limit
    except Exception as e:
        print(f"[discord] {e}")

def disc_ok(msg):   disc(msg, 0x57F287, "✅ Success")
def disc_warn(msg): disc(msg, 0xFEE75C, "⚠️ Warning")
def disc_err(msg):  disc(msg, 0xED4245, "❌ Error")
def disc_info(msg): disc(msg, 0x5865F2, "ℹ️ Autopilot")

# ── Cooldowns ──────────────────────────────────────────────────────────
def cd_read():
    return json.loads((STATE / "cooldowns.json").read_text())

def cd_write(data):
    (STATE / "cooldowns.json").write_text(json.dumps(data, indent=2))

def cd_lock(tool, minutes):
    data = cd_read()
    until = (datetime.now() + timedelta(minutes=minutes)).isoformat()
    data[tool]["locked_until"] = until
    data[tool]["consecutive_fails"] = data[tool].get("consecutive_fails", 0) + 1
    cd_write(data)
    disc_warn(f"**{tool}** rate-limited — locked for {minutes}min\nUnlocks at `{until}`")

def cd_unlock(tool):
    data = cd_read()
    data[tool]["locked_until"] = None
    data[tool]["consecutive_fails"] = 0
    cd_write(data)

def cd_available(tool):
    data = cd_read()
    locked_until = data.get(tool, {}).get("locked_until")
    if locked_until is None:
        return True
    return datetime.now() > datetime.fromisoformat(locked_until)

# ── Rate limit probe ───────────────────────────────────────────────────
RATE_PATTERNS = [
    "rate limit", "429", "quota exceeded", "resource_exhausted",
    "try again in", "too many requests", "rate_limit"
]

def is_rate_limited(output: str) -> bool:
    low = output.lower()
    return any(p in low for p in RATE_PATTERNS)

def probe_tool(tool):
    """Quick liveness check — unlock if previously locked and now responsive."""
    if not cd_available(tool):
        return  # still in cooldown window

    try:
        if tool == "agy":
            r = subprocess.run(
                ["agy", "--dangerously-skip-permissions", "-p", "respond with only: ok"],
                capture_output=True, text=True, timeout=20
            )
            out = r.stdout + r.stderr
            if is_rate_limited(out):
                cd_lock("agy", 30)
            else:
                cd_unlock("agy")

        elif tool == "gemini":
            r = subprocess.run(
                ["gemini", "-p", "say ok"],
                capture_output=True, text=True, timeout=20
            )
            out = r.stdout + r.stderr
            if is_rate_limited(out):
                cd_lock("gemini", 0)   # gemini resets fast
            else:
                cd_unlock("gemini")

        elif tool == "ngrok":
            url = (STATE / "ngrok_url.txt").read_text().strip()
            if not url:
                return
            r = requests.get(f"{url}/v1/models",
                             headers={"Authorization": "Bearer x"}, timeout=10)
            if r.status_code in (200, 401):
                cd_unlock("ngrok")
            else:
                cd_lock("ngrok", 0)

        elif tool == "copilot":
            r = subprocess.run(
                ["copilot", "--allow-all", "-p", "respond with only: ok"],
                capture_output=True, text=True, timeout=20
            )
            out = r.stdout + r.stderr
            if is_rate_limited(out):
                cd_lock("copilot", 5)
            else:
                cd_unlock("copilot")

        elif tool == "ollama":
            r = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=10)
            if r.returncode == 0:
                cd_unlock("ollama")

        elif tool == "freebuff":
            r = subprocess.run(["which", "freebuff"], capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                # Check if freebuff binary exists and has the auth token
                auth = subprocess.run(
                    ["sh", "-c", 'cat ~/.config/manicode/credentials.json 2>/dev/null | grep -q authToken'],
                    capture_output=True, text=True, timeout=5
                )
                if auth.returncode == 0:
                    cd_unlock("freebuff")

        elif tool == "codebuff-mod":
            r = subprocess.run(["which", "cbm"], capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                # Check if binary downloaded and providers configured
                providers = subprocess.run(
                    ["sh", "-c", 'cat ~/.config/manicode/providers.json 2>/dev/null | grep -q opencode'],
                    capture_output=True, text=True, timeout=5
                )
                if providers.returncode == 0:
                    cd_unlock("codebuff-mod")

    except subprocess.TimeoutExpired:
        pass   # tool slow but not rate-limited
    except Exception as e:
        print(f"[probe:{tool}] {e}")

def probe_loop():
    while True:
        for tool in ["agy", "copilot", "gemini", "freebuff", "codebuff-mod", "ngrok", "ollama"]:
            probe_tool(tool)
        time.sleep(60)

# ── Tunnel manager ─────────────────────────────────────────────────────
def kaggle_push_notebook():
    disc_info("🚀 Pushing vLLM notebook to Kaggle...")
    nb_dir = str(NOTEBOOKS)

    # inject ngrok token into notebook
    nb_path = NOTEBOOKS / "vllm_server.ipynb"
    nb = json.loads(nb_path.read_text())
    for cell in nb["cells"]:
        cell["source"] = [
            s.replace("PLACEHOLDER", NGROK_TOK) for s in cell["source"]
        ]
    nb_path.write_text(json.dumps(nb))

    r = subprocess.run(
        ["kaggle", "kernels", "push", "-p", nb_dir],
        capture_output=True, text=True
    )
    if r.returncode != 0:
        disc_err(f"Kaggle push failed:\n```{r.stderr[:500]}```")
        return False
    disc_info("Kaggle notebook pushed — waiting for GPU to spin up (~3 min)...")
    return True

def kaggle_poll_ngrok():
    kernel_id = f"{KAGGLE_UN}/autopilot-vllm-server"
    for attempt in range(40):   # up to ~20 min
        time.sleep(30)
        try:
            _r = subprocess.run(
                ["kaggle", "kernels", "output", kernel_id, "-p", "/tmp/kaggle_out"],
                capture_output=True, text=True, timeout=30
            )
            # also check logs
            r2 = subprocess.run(
                ["kaggle", "kernels", "status", kernel_id],
                capture_output=True, text=True, timeout=15
            )
            status_out = r2.stdout + r2.stderr

            if "error" in status_out.lower():
                disc_err("Kaggle kernel errored — will retry in 10 min")
                return None

            # scan output files for ngrok URL
            out_dir = Path("/tmp/kaggle_out")
            if out_dir.exists():
                for f in out_dir.rglob("*.txt"):
                    txt = f.read_text()
                    match = re.search(r"NGROK_URL:(https://[^\s]+)", txt)
                    if match:
                        url = match.group(1)
                        (STATE / "ngrok_url.txt").write_text(url)
                        disc_ok(f"🌐 Kaggle ngrok tunnel active: `{url}`")
                        return url

            # also check stdout of status for URL
            match = re.search(r"NGROK_URL:(https://[^\s]+)", status_out)
            if match:
                url = match.group(1)
                (STATE / "ngrok_url.txt").write_text(url)
                disc_ok(f"🌐 Kaggle ngrok tunnel active: `{url}`")
                return url

        except Exception as e:
            print(f"[kaggle_poll] {e}")

    disc_err("Kaggle tunnel never came up after 20 min")
    return None

def tunnel_manager_loop():
    while True:
        ngrok_url = (STATE / "ngrok_url.txt").read_text().strip()
        tunnel_alive = False

        if ngrok_url:
            try:
                r = requests.get(f"{ngrok_url}/v1/models",
                                 headers={"Authorization": "Bearer x"}, timeout=10)
                tunnel_alive = r.status_code in (200, 401)
            except requests.RequestException as e:
                tunnel_alive = False
                print(f"[tunnel] health check failed: {e}")

        if not tunnel_alive:
            (STATE / "ngrok_url.txt").write_text("")
            cd_lock("ngrok", 0)
            if kaggle_push_notebook():
                url = kaggle_poll_ngrok()
                if url:
                    cd_unlock("ngrok")
            time.sleep(600)   # wait 10 min before retry if failed
        else:
            time.sleep(120)   # check tunnel health every 2 min

# ── Planner ────────────────────────────────────────────────────────────
ROUTING = {
    "file-edit":           ["copilot", "opencode", "freebuff", "codebuff-mod", "agy", "openrouter", "ollama"],
    "backend-python":      ["copilot", "opencode", "freebuff", "codebuff-mod", "agy", "openrouter", "ollama"],
    "frontend":            ["copilot", "opencode", "freebuff", "codebuff-mod", "agy", "openrouter", "ollama"],
    "planning":            ["openrouter", "freebuff", "codebuff-mod", "copilot", "agy", "opencode", "ollama"],
    "multi-file-refactor": ["copilot", "opencode", "freebuff", "codebuff-mod", "agy", "openrouter", "ollama"],
    "ml-task":             ["ngrok", "openrouter", "freebuff", "codebuff-mod", "copilot", "opencode", "ollama"],
    "backtest":            ["ngrok", "openrouter", "freebuff", "codebuff-mod", "copilot", "opencode", "ollama"],
    "heavy-reasoning":     ["ngrok", "openrouter", "freebuff", "codebuff-mod", "copilot", "opencode", "ollama"],
}

def classify_task(task_text: str) -> str:
    t = task_text.lower()
    if any(w in t for w in ["train", "xgboost", "backtest", "model", "ml", "dataset"]):
        return "ml-task"
    if any(w in t for w in ["refactor", "rename", "move", "restructure"]):
        return "multi-file-refactor"
    if any(w in t for w in ["plan", "design", "architecture", "brainstorm"]):
        return "planning"
    if any(w in t for w in ["tsx", "react", "frontend", "css", "component"]):
        return "frontend"
    if any(w in t for w in ["py", "python", "api", "route", "backend", "fastapi"]):
        return "backend-python"
    return "file-edit"

def pick_tool(task_type: str) -> str | None:
    for tool in ROUTING.get(task_type, ROUTING["file-edit"]):
        if cd_available(tool):
            # extra check: ngrok needs non-empty URL
            if tool == "ngrok":
                url = (STATE / "ngrok_url.txt").read_text().strip()
                if not url:
                    continue
            return tool
    return None

def auto_plan() -> list[dict]:
    """Ask available coding agents to analyze the codebase and return tasks."""
    planner = "copilot" if cd_available("copilot") else \
              "opencode" if cd_available("opencode") else \
              "openrouter" if cd_available("openrouter") and OR_KEY and OR_KEY != "FILL_IN_YOUR_OPENROUTER_KEY_HERE" else \
              "agy" if cd_available("agy") else None
    if not planner:
        disc_warn("No planner available — skipping plan cycle")
        return []

    prompt = (
        "Analyze this codebase and return a JSON array of tasks to fix/improve. "
        "Each task: {\"id\":\"t-N\", \"type\":\"file-edit|backend-python|ml-task|"
        "planning|multi-file-refactor|frontend\", \"priority\":1-5, "
        "\"prompt\":\"specific instruction\", \"file\":\"path/if/relevant\"}. "
        "Return ONLY the JSON array, no markdown, no explanation. "
        "Focus on: TODO comments, broken imports, failing tests, missing error handling, "
        "unused code, security issues. Max 10 tasks."
    )

    disc_info(f"🧠 Planning cycle started via **{planner}**...")

    parsed_out = False

    try:
        if planner == "copilot":
            cmd = ["copilot", "--add-dir", WORKDIR, "--allow-all", "-p", prompt]
        elif planner == "opencode":
            cmd = ["opencode", "run", prompt, "--dir", WORKDIR]
        elif planner == "openrouter":
            # Use OpenRouter API directly (no subprocess needed)
            r_api = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {OR_KEY}",
                         "Content-Type": "application/json"},
                json={"model": OR_MODEL,
                      "messages": [{"role": "user", "content": prompt}],
                      "max_tokens": 4096},
                timeout=120
            )
            out = r_api.json()["choices"][0]["message"]["content"]
            parsed_out = True
        elif planner == "gemini":
            cmd = ["gemini", "-p", prompt]
        else:
            cmd = ["agy", "--dangerously-skip-permissions", "-p", prompt,
                   "--workdir", WORKDIR]

        if not parsed_out:
            r = subprocess.run(cmd, capture_output=True, text=True,
                               timeout=120, cwd=WORKDIR)
            out = r.stdout + r.stderr

        if is_rate_limited(out):
            cd_lock(planner, 30 if planner == "agy" else 0)
            return []

        # extract JSON from output
        match = re.search(r"\[.*\]", out, re.DOTALL)
        if not match:
            disc_warn(f"Planner returned no parseable JSON:\n```{out[:300]}```")
            return []

        tasks = json.loads(match.group(0))
        tasks.sort(key=lambda t: t.get("priority", 5))
        disc_info(f"📋 Plan ready — **{len(tasks)} tasks** queued\n" +
                  "\n".join(f"• [{t['type']}] {t['prompt'][:60]}" for t in tasks[:5]))
        return tasks

    except Exception as e:
        disc_err(f"Planning failed: {e}")
        return []

def run_task(task: dict):
    tool = pick_tool(task["type"])
    if not tool:
        disc_warn(f"All tools locked — skipping task `{task['id']}`")
        return

    prompt   = task["prompt"]
    task_id  = task.get("id", f"t-{int(time.time())}")
    workdir  = task.get("workdir", WORKDIR)
    disc_info(f"▶️ `{task_id}` → **{tool}**\n`{prompt[:100]}`")

    try:
        if tool == "agy":
            cmd = ["agy", "--dangerously-skip-permissions", "-p", prompt,
                   "--workdir", workdir]
            timeout = 600

        elif tool == "gemini":
            cmd = ["gemini", "-p", f"In the project at {workdir}: {prompt}"]
            timeout = 300

        elif tool == "opencode":
            cmd = ["opencode", "run", prompt, "--dir", workdir]
            timeout = 600

        elif tool == "ngrok":
            url = (STATE / "ngrok_url.txt").read_text().strip()
            r = requests.post(f"{url}/v1/chat/completions",
                headers={"Authorization": "Bearer x", "Content-Type": "application/json"},
                json={"model": "Qwen/Qwen2.5-72B-Instruct",
                      "messages": [{"role": "user", "content": prompt}],
                      "max_tokens": 4096},
                timeout=120
            )
            result = r.json()["choices"][0]["message"]["content"]
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            (RESULTS / f"{task_id}_{ts}.json").write_text(
                json.dumps({"task": task, "tool": tool, "result": result}, indent=2))
            disc_ok(f"✅ `{task_id}` done via **{tool}**\n```{result[:300]}```")
            return

        elif tool == "copilot":
            cmd = ["copilot", "--add-dir", workdir, "--allow-all", "-p", prompt]
            timeout = 600

        elif tool == "openrouter":
            r_api = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {OR_KEY}",
                         "Content-Type": "application/json"},
                json={"model": OR_MODEL,
                      "messages": [{"role": "user", "content": prompt}],
                      "max_tokens": 4096},
                timeout=120
            )
            result = r_api.json()["choices"][0]["message"]["content"]
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            (RESULTS / f"{task_id}_{ts}.json").write_text(
                json.dumps({"task": task, "tool": tool, "result": result}, indent=2))
            disc_ok(f"✅ `{task_id}` done via **{tool}**\n```{result[:300]}```")
            return

        elif tool == "ollama":
            cmd = ["ollama", "run", "qwen2.5:7b", prompt]
            timeout = 120

        elif tool == "freebuff":
            # Freebuff is a TUI tool — log the task and notify for interactive use
            disc_warn(f"🖥️ `{task_id}` routed to **freebuff** — TUI tool, run manually:\n  `cd {workdir} && freebuff`\nPrompt: {prompt[:200]}")
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            (RESULTS / f"{task_id}_{ts}.json").write_text(
                json.dumps({"task": task, "tool": tool, "note": "TUI tool — requires interactive use"}, indent=2))
            return

        elif tool == "codebuff-mod":
            disc_warn(f"🖥️ `{task_id}` routed to **codebuff-mod** — TUI tool, run manually:\n  `cd {workdir} && codebuff-mod --free \"{prompt[:100]}...\"`")
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            (RESULTS / f"{task_id}_{ts}.json").write_text(
                json.dumps({"task": task, "tool": tool, "note": "TUI tool — requires interactive use"}, indent=2))
            return

        r = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=timeout, cwd=workdir)
        out = r.stdout + r.stderr

        if is_rate_limited(out):
            minutes = 30 if tool == "agy" else 5
            cd_lock(tool, minutes)
            disc_warn(f"🔄 `{task_id}` — **{tool}** hit rate limit, retrying with fallback...")
            # retry once with next available tool
            task_copy = dict(task)
            run_task(task_copy)
            return

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        (RESULTS / f"{task_id}_{ts}.json").write_text(
            json.dumps({"task": task, "tool": tool,
                        "stdout": r.stdout, "stderr": r.stderr,
                        "exit_code": r.returncode}, indent=2))

        status = "✅" if r.returncode == 0 else "⚠️"
        disc_ok(f"{status} `{task_id}` done via **{tool}** (exit {r.returncode})\n"
                f"```{r.stdout[:300]}```")

    except subprocess.TimeoutExpired:
        disc_err(f"⏱️ `{task_id}` timed out on **{tool}**")
    except Exception as e:
        disc_err(f"💥 `{task_id}` crashed on **{tool}**: {e}")

# ── Main loop ──────────────────────────────────────────────────────────
def main():
    disc_info("🤖 **Autopilot started**\nBeginning self-planning loop. "
              "Tools: copilot · opencode · freebuff · codebuff-mod · agy · openrouter · ngrok/vLLM · ollama")

    # background threads
    threading.Thread(target=probe_loop,          daemon=True).start()
    threading.Thread(target=tunnel_manager_loop, daemon=True).start()

    disc_info("🔍 Probe thread started — checking tool availability every 60s\n"
              "🌐 Tunnel manager started — Kaggle vLLM notebook launching...")

    while True:
        try:
            tasks = auto_plan()
            if not tasks:
                disc_info("💤 No tasks found — re-planning in 5 minutes")
                time.sleep(300)
                continue

            for task in tasks:
                run_task(task)
                time.sleep(10)   # brief pause between tasks

            disc_info("✅ Plan complete — re-planning in 5 minutes")
            time.sleep(300)

        except KeyboardInterrupt:
            disc_warn("🛑 Autopilot stopped by user")
            break
        except Exception as e:
            disc_err(f"Main loop error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
