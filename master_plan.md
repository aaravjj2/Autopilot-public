# APEX Master Plan (Canonical)

This file is the single execution control-plane for APEX.

It intentionally avoids duplicating all 260 day documents inline. The prior embedded version created non-actionable boilerplate at massive size and has been deprecated.

---

## 1) Authoritative Plan Sources

- Architecture + formulas + schemas + API contracts + 10-week strategic roadmap:
  - `docs/architecture/master_plan_arch.md`
- Daily execution plan artifacts:
  - `one-year-daily/day-001.md` ... `one-year-daily/day-260.md`
- Daily quality gate verifier:
  - `scripts/verification/verify_roadmap_daily.py`

---

## 2) Program Guardrails

- Paper-only execution remains mandatory.
- `M01_PAPER_REQUIRED` remains first risk gate in all execution paths.
- No raw runtime DB access outside repository abstractions.
- Optional intelligence integrations must soft-fail safely.
- Every daily deliverable must include:
  - concrete file targets
  - named symbols/functions
  - objective verification commands
  - browser-visible acceptance checks where applicable

---

## 3) 260-Day Completion Status

- Daily files present: `260/260`
- Day range covered: `001-260`
- Baseline structural format check: pass (header/token/line-count only)

Validation command:

```bash
python scripts/verification/verify_roadmap_daily.py --start 1 --end 260
```

---

## 4) Regeneration Standard (No Boilerplate Loops)

When regenerating any day files:

1. Do not use repeated generic templates for work packages.
2. Each day must contain unique, implementation-specific instructions.
3. Each work package must map to identifiable code units (path + symbol).
4. Verification commands must target the day’s concrete changes.
5. Run verifier and keep this file updated with status.

---

## 5) Current Execution Policy

- Use `docs/architecture/master_plan_arch.md` as strategic reference.
- Execute from `one-year-daily/day-001.md` onward with test-first sequencing.
- If a day file lacks concrete specificity, regenerate that day before execution.

---

## 6) Regeneration Changelog

- `2026-05-28`: regenerated `one-year-daily/day-001.md` through `one-year-daily/day-020.md` with unique, symbol-level work packages and targeted verification commands.
- Validation executed:
  - `python scripts/verification/verify_roadmap_daily.py --start 1 --end 20`
  - placeholder token scan across day 001-020 (no matches)
  - objective-line uniqueness check (`160/160` unique; does not imply full body uniqueness)
  - file-reference and pytest-target integrity checks (no missing paths/targets)

---

*End of canonical master plan.*

