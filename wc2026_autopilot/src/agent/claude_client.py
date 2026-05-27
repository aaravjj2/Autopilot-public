"""LLM client with provider auto-routing + shell brain fallback."""

from __future__ import annotations

import json
import os
import re
import subprocess
from typing import Any

from config import bootstrap_env

bootstrap_env()


def _extract_json(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"```(?:json)?\\s*(\{.*?\})\\s*```", text, re.DOTALL)
        if m:
            return json.loads(m.group(1))
        m2 = re.search(r"(\{.*\})", text, re.DOTALL)
        if m2:
            return json.loads(m2.group(1))
        raise


def _route() -> str:
    brain = (os.getenv("WC_LLM_BRAIN") or "auto").lower()
    if brain != "auto":
        return brain
    if os.getenv("GROQ_API_KEY"):
        return "groq"
    if os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
        return "gemini"
    if os.getenv("OPENROUTER_KEY"):
        return "openrouter"
    host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    try:
        import requests

        if requests.get(f"{host.rstrip('/')}/api/tags", timeout=2).ok:
            return "ollama"
    except Exception:
        pass
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic"
    return "shell"


def _call_openai_compat(base_url: str, api_key: str, model: str, system: str, prompt: str) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=base_url)
    rsp = client.chat.completions.create(
        model=model,
        temperature=0.2,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    )
    return rsp.choices[0].message.content or "{}"


def _call_shell_brain(system: str, prompt: str) -> str:
    cmd = (os.getenv("WC_SHELL_BRAIN_CMD") or "ollama run llama3.2:3b").strip()
    data = f"SYSTEM:\n{system}\n\nUSER:\n{prompt}\n"
    proc = subprocess.run(
        cmd,
        shell=True,
        input=data,
        text=True,
        capture_output=True,
        timeout=120,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Shell brain failed: {proc.stderr[:200]}")
    return proc.stdout


def call_claude(prompt: str, system: str) -> dict:
    """Compatibility function name; uses any available keys from keys.env/.env."""
    route = _route()
    last_err: Exception | None = None
    for attempt in range(3):
        try:
            if route == "groq":
                text = _call_openai_compat(
                    "https://api.groq.com/openai/v1",
                    os.environ["GROQ_API_KEY"],
                    os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
                    system,
                    prompt,
                )
            elif route == "gemini":
                text = _call_openai_compat(
                    "https://generativelanguage.googleapis.com/v1beta/openai/",
                    os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "",
                    os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
                    system,
                    prompt,
                )
            elif route == "openrouter":
                text = _call_openai_compat(
                    "https://openrouter.ai/api/v1",
                    os.environ["OPENROUTER_KEY"],
                    os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free"),
                    system,
                    prompt,
                )
            elif route == "ollama":
                text = _call_openai_compat(
                    f"{os.getenv('OLLAMA_HOST', 'http://localhost:11434').rstrip('/')}/v1",
                    "ollama",
                    os.getenv("OLLAMA_MODEL", "llama3.2:3b"),
                    system,
                    prompt,
                )
            elif route == "anthropic":
                import anthropic

                client = anthropic.Anthropic()
                response = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=1000,
                    system=system,
                    messages=[{"role": "user", "content": prompt}],
                )
                text = response.content[0].text
            else:
                text = _call_shell_brain(system, prompt)
            return _extract_json(text)
        except Exception as exc:
            last_err = exc
            if attempt == 2:
                break
    raise ValueError(f"LLM returned unparseable response after 3 attempts: {last_err}")
