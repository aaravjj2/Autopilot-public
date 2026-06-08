# Codebase analysis — 2026-06-08

## Current state
- 411 tests collected (via pytest --co)
- Playwright is installed (v0.8.0) and working, but dashboard test fails because
  port 8501 runs MoneyPrinterTurbo, not APEX Monitor
- All non-Playwright tests pass (101 passed in first batch)
- utcnow() deprecation warnings only exist in external/polymarket-mcp-server
  (submodule, not our code)
- 3 critical blockers noted in health report (Groq 401, Ollama not running,
  OpenCode Zen 404)
- broker.py line 79 just has "utcnow" in a log string — not a function call
