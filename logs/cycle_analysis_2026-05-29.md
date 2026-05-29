═══════════════════════════════════════════════════════════════════
 APEX Autopilot — Codebase Analysis Cycle Report
═══════════════════════════════════════════════════════════════════

Date: 2026-05-29
Model: deepseek-v4-flash-free (opencode-zen)

EXECUTIVE SUMMARY
──────────────────
364 tests total: 355 PASS, 9 FAIL, 1 SKIP (97.5% pass rate)

The 9 failures are ALL in tests/test_gemini_native.py and stem from
a single root cause: call_with_retries() signature mismatch in
gemini_native.py. The underlying retry.py was refactored (all kwargs
became keyword-only after fn), but the caller in gemini_native.py
wasn't updated to match.

FAILING TESTS (9)
─────────────────
1. TestUsesQueryKeyAuth::test_aq_lowercase_still_true
   - uses_query_key_auth("aq.test-key") returns False instead of True
   - Cause: .startswith("AQ.") is case-sensitive; lowercase "aq." not matched

2-9. TestGenerateContent::test_happy_path_returns_text
     TestGenerateContent::test_without_system_instruction
     TestGenerateContent::test_no_candidates_raises
     TestGenerateContent::test_empty_text_raises
     TestGenerateContent::test_non_dict_response_raises
     TestGenerateContent::test_model_id_strips_prefix
     TestGenerateContent::test_retry_on_http_error
     TestGenerateContent::test_parts_multiple_segments_joined
   - All raise TypeError: call_with_retries() takes 1 positional arg but 2
   - Root: gemini_native.py:61 calls
     call_with_retries("gemini.generateContent", _post, max_attempts=3)
   - But retry.py now accepts only fn as positional; label is keyword-only
   - All other callers (5 sites) use the correct pattern:
     call_with_retries(lambda: ..., max_attempts=..., backoff_seconds=..., log_label=...)

ROOT CAUSE DETAIL
─────────────────
File: src/apex/core/retry.py
  def call_with_retries(
      fn: Callable[[], T],      # position 0
      *,                         # keyword-only after *
      max_attempts: int,
      backoff_seconds: float,    # REQUIRED (no default!)
      log_label: str = "",
  ) -> T:

File: src/apex/core/gemini_native.py:61 (INCORRECT)
  call_with_retries("gemini.generateContent", _post, max_attempts=3)
  # ^^^ passes string as fn (0), _post as extra positional → TypeError

All other callers (5/5) use keyword args correctly:
  src/apex/layers/l0/ingestion.py — correct
  src/apex/layers/l3/execution.py — correct (2 call sites)
  src/apex/integrations/broker.py  — correct
  src/apex/services/engine.py      — correct

Note: backoff_seconds is REQUIRED with no default — all callers
provide it explicitly. gemini_native.py would also have failed at
runtime for this reason after the signature fix.

SECONDARY ISSUES
────────────────
1. Print statements (50+): autopilot-continuous.py, scripts/, scratch.py
   - Should use get_logger(__name__) per APEX conventions

2. Broad except handlers (30): mostly in test files (acceptable) +
   21 in production code (should be refined)

3. Deprecation warnings (18):
   - SQLModel Pydantic v2 ConfigDict deprecation (3)
   - ChromaDB Pydantic v2.11 model_fields deprecation (15)

4. retry.py: backoff_seconds has NO default value
   - All callers provide it, so no runtime issue
   - But could be safer with a default (e.g. 2.0)

PRIORITIZED FIX PLAN
────────────────────
P0 — Fix failing tests (9 tests, 1 root cause)
  [P0a] gemini_native.py:61 — fix call_with_retries signature
  [P0b] gemini_native.py:22 — fix case-sensitive AQ. check

P1 — No other failing tests to fix

P2 — Cleanup (low priority / maintenance)
  [P2a] Convert 50 print() statements to logger calls
  [P2b] Add backoff_seconds default to retry.py

═══════════════════════════════════════════════════════════════════