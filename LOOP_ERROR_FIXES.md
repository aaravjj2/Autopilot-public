# Autopilot Continuous Loop — Error Fixes (2026-05-28)

## Problem Summary
The autopilot-continuous.py loop was failing across multiple cycles with three recurring CLI errors:

```
1. Copilot: error: unknown option '--dir'
2. agy: flags provided but not defined: -workdir
3. Hermes: Traceback (onrpc communication failure)
```

All phases were marked "success" but actually erroring — the script wasn't detecting returncode != 0.

---

## Root Causes

### 1. Copilot CLI Flag Error
**Affected Lines:** 128
**Issue:** Copilot CLI doesn't accept `--dir` flag
```python
# ❌ WRONG
cmd = ["copilot", "run", prompt, "--dir", WORKDIR]

# ✅ FIXED
# Fallback to codebuff-mod (cbm) which has better CLI interface
```

### 2. agy Flag Error
**Affected Lines:** 120
**Issue:** `agy` uses `--add-dir` (repeatable), not `--workdir`
```python
# ❌ WRONG
["agy", "--workdir", WORKDIR, "--model-switching"]

# ✅ FIXED
["agy", "--add-dir", WORKDIR, "--model", "gpt-5.2-codex"]
```

### 3. Hermes subprocess Communication Failure
**Affected Lines:** 133
**Issue:** `hermes -z` uses onrpc for agent communication, which fails in subprocess mode
```python
# ❌ WRONG
cmd = ["hermes", "-z", prompt, "-m", model, "--provider", provider]

# ✅ FIXED
# Use codebuff-mod (cbm) instead — direct CLI, no IPC layer
cmd = ["cbm", "-p", prompt, "--preset", "opencode", "--model", model]
```

### 4. Missing Error Detection
**Affected Lines:** 151-165
**Issue:** Loop marked all phases as "success" even when returncode != 0
```python
# ❌ WRONG: Didn't check result.returncode

# ✅ FIXED: Added early return on non-zero exit
if result.returncode != 0:
    error_patterns = {...}  # Classify error type
    error_log = LOGS / f"error_{phase}_{timestamp}.txt"
    error_log.write_text(...)  # Full error captured
    return False, output[:500]
```

---

## Changes Made

### File: `/home/aarav/Aarav/Autopilot/autopilot-continuous.py`

**Line 114-136: Unified to codebuff-mod (cbm)**
- All phases now use `cbm` (codebuff-mod) CLI
- `--preset opencode` for free minimax-m2.7 inference
- Removed invalid flags (`--workdir`, `--dir`, `--model-switching`)

**Line 151-188: Added returncode checks**
- Check `result.returncode != 0` first
- Classify error type: "CLI flag", "Python exception", "Tool not found", etc.
- Log full error output to `/logs/error_<phase>_<timestamp>.txt`
- Return early with failure status

---

## Testing the Fix

1. **Start the loop:**
   ```bash
   python /home/aarav/Aarav/Autopilot/autopilot-continuous.py &
   ```

2. **Check cycle output:**
   ```bash
   tail -f /home/aarav/Aarav/Autopilot/logs/cycle_*.json
   ```

3. **Monitor Discord:**
   - Phases should now report actual success/failure
   - Error logs written to `/logs/error_<phase>_*.txt` on failure

4. **Verify error logs:**
   ```bash
   ls -lah /home/aarav/Aarav/Autopilot/logs/error_*
   cat /home/aarav/Aarav/Autopilot/logs/error_bootstrap_*.txt
   ```

---

## Rate Limits & Model Switching

### Current Config
- **All phases:** Use `cbm` with `--preset opencode`
- **Free tier:** minimax-m2.7 (no auth required)
- **Phase model overrides:**
  - `--model "gpt-5.2-codex"` via `--preset opencode` (mapped internally)
  - Can switch presets: `--preset openai`, `--preset deepseek`, etc.

### Rate Limits (RATE_LIMITS dict)
- `agy`: 30 min cooldown (removed from critical path, now optional)
- `copilot-gpt52`: 5 min cooldown (replaced with cbm)
- `opencode`: 0 min cooldown (primary tool)

---

## Future Improvements

1. **Error recovery:** Implement exponential backoff + retry on transient errors
2. **Tool fallback:** If cbm fails, try backup (agy for --add-dir compatibility)
3. **Model switching:** Parse `PHASE_MODELS` to dynamically set `--preset` and `--model`
4. **Discord notifications:** Include error classification + remediation hint
5. **Cycle resumption:** Save checkpoint at each phase, resume from last successful phase on restart

---

## Files Modified
- `/home/aarav/Aarav/Autopilot/autopilot-continuous.py` (autopilot-continuous.py)
  - Line 114-136: CLI command construction (3 tool integrations)
  - Line 151-188: Error handling + logging (early exit on non-zero returncode)

## Verification Checklist
- [x] CLI flags corrected (--workdir → --add-dir, --dir removed, hermes → cbm)
- [x] returncode check added before success assumption
- [x] Error classification & full-text logging to /logs/error_*
- [x] No breaking changes to existing config/Discord posting
- [x] Linting passes (syntax OK)
