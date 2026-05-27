from __future__ import annotations

import os

import config
from agent import claude_client


def test_get_logger_initializes():
    log = config.get_logger("wc2026")
    assert log.name == "wc2026"


def test_shell_brain_command_echoes(monkeypatch):
    monkeypatch.setenv("WC_SHELL_BRAIN_CMD", "cat")
    out = claude_client._call_shell_brain("SYS", "USR")
    assert "SYSTEM" in out and "USER" in out


def test_bootstrap_env_loads_local_env(tmp_path, monkeypatch):
    # Create a local .env at PROJECT_ROOT and ensure it's loaded.
    env_path = config.PROJECT_ROOT / ".env"
    try:
        env_path.write_text("WC_BOOTSTRAP_TEST=1\n", encoding="utf-8")
        monkeypatch.setattr(config, "_ENV_LOADED", False)
        config.bootstrap_env()
        assert os.getenv("WC_BOOTSTRAP_TEST") == "1"
    finally:
        try:
            env_path.unlink()
        except FileNotFoundError:
            pass
