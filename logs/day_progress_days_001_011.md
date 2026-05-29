## 260-Day Plan Recovery Log (Days 1-11)

- Timestamp: 2026-05-27
- Recovery owner: Cursor agent
- Failure point: demo startup seeding crashed on `sqlite3.IntegrityError: UNIQUE constraint failed: audit_log.event_id`
- Root cause: duplicate `event_id` insert during demo reseed path when existing DB already contained colliding audit IDs.
- Fix applied: `SQLiteStore.append_event()` now uses `INSERT OR IGNORE` for `audit_log` writes, making reseed/restart idempotent.
- Test-first evidence:
  - Added `test_demo_seed_handles_duplicate_audit_event_ids` in `tests/test_demo_mode.py` (failed before fix, passed after fix).
  - Executed: `PYTHONPATH=src python -m pytest tests/test_demo_mode.py tests/test_001_regression.py tests/test_011_regression.py -q`
  - Result: `17 passed`
- Runtime verification:
  - Executed seeding twice against real DB (`data/audit.db`).
  - Result: both runs returned success with no crash.

### Day Status (1-11)

- Day 1: PASS (`tests/test_001_regression.py`)
- Day 2: NOT_VERIFIABLE (no dedicated Day 2 workflow/test artifact found in repository)
- Day 3: NOT_VERIFIABLE (no dedicated Day 3 workflow/test artifact found in repository)
- Day 4: NOT_VERIFIABLE (no dedicated Day 4 workflow/test artifact found in repository)
- Day 5: NOT_VERIFIABLE (no dedicated Day 5 workflow/test artifact found in repository)
- Day 6: NOT_VERIFIABLE (no dedicated Day 6 workflow/test artifact found in repository)
- Day 7: NOT_VERIFIABLE (no dedicated Day 7 workflow/test artifact found in repository)
- Day 8: NOT_VERIFIABLE (no dedicated Day 8 workflow/test artifact found in repository)
- Day 9: NOT_VERIFIABLE (no dedicated Day 9 workflow/test artifact found in repository)
- Day 10: NOT_VERIFIABLE (no dedicated Day 10 workflow/test artifact found in repository)
- Day 11: PASS (`tests/test_011_regression.py`)

### Remaining Blockers

- No code blocker remains for the Day 1-11 recovery path.
- Operational warning remains: `pytest-asyncio` deprecation warning about unset `asyncio_default_fixture_loop_scope` in test config.

### Day 2-10 Verification Harness Results

- Timestamp: 2026-05-27T13:47:52.208308+00:00
- Runner: `python scripts/verification/verify_days_002_010.py --days 2-10`

| Day | Status | Deliverable |
|---|---|---|
| 002 | FAIL | PR checklist: Playwright single `:8000` webServer + `.env.local.example` (verification) |
| 003 | FAIL | docs/runtime/engine-singleton-audit.md — no hot-path `build_engine()` (verification) |
| 004 | FAIL | docs/scheduler/job-registry.md — APScheduler idempotency sign-off (verification) |
| 005 | FAIL | CI green: `.github/workflows/ci.yml` + Playwright webServer only (verification) |
| 006 | FAIL | Verify `start-unified.sh` health-wait on `:8000` — no `:8001` in default path |
| 007 | FAIL | Verify `package.json` dev script = apex + frontend only (2 processes) |
| 008 | FAIL | Verify pid/log rotation in start-unified.sh |
| 009 | FAIL | Verify graceful stop kills only unified backend |
| 010 | FAIL | DB02 EXIT: operator path never starts `:8001` (verification sign-off) |

#### Evidence
- Day 002 (FAIL)
  - [PASS] Playwright test discovery is tests/e2e: 16:  testDir: './tests/e2e', | cmd: `rg -n "testDir:\s*'./tests/e2e'" "/home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts"`
  - [FAIL] Playwright webServer uses backend :8000: error: Found argument '--port 8000' which wasn't expected, or isn't valid in this context

USAGE:
    
    rg [OPTIONS] PATTERN [PATH ...]
    rg [OPTIONS] -e PATTERN ... [PATH ...]
    rg [OPTIONS] -f PATTERNFILE ... [PATH ...]
    rg [OPTIONS] --files [PATH ...]
    rg [OPTIONS] --type-list
    command | rg [OPTIONS] PATTERN
    rg [OPTIONS] --help
    rg [OPTIONS] --version

For more information try --help | cmd: `rg -n "--port 8000" "/home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts"`
  - [FAIL] Frontend :8001 removed from default path: /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts:32:  // DB01: single unified backend on :8000 — :8001 legacy removed | cmd: `rg -n "8001" "/home/aarav/Aarav/Autopilot/autopilot-local/frontend"`
  - [PASS] CI starts backend before waiting health: workflow order is Start APEX backend -> Wait for APEX health
  - [PASS] Backend /health responds: status=healthy | cmd: `curl -sS -f http://127.0.0.1:8000/health`
  - [FAIL] Backend /api/health responds: HTTP returned JSON but missing expected status field | cmd: `curl -sS -f http://127.0.0.1:8000/api/health`
  - [FAIL] Frontend landing references /dashboard: unexpected pattern state | cmd: `rg -n "href="/dashboard"" "/home/aarav/Aarav/Autopilot/autopilot-local/frontend/app/page.tsx"`
  - [FAIL] Unified dev script references apex+web: /home/aarav/Aarav/Autopilot/autopilot-local/package.json:5:    "dev": "concurrently -n apex,web -c blue,green \"npm run dev:apex\" \"npm run dev:frontend\"", | cmd: `rg -n "dev": "concurrently -n apex,web" "/home/aarav/Aarav/Autopilot/autopilot-local/package.json"`
  - [PASS] Day 002 .env.local.example exists: found /home/aarav/Aarav/Autopilot/autopilot-local/.env.local.example
- Day 003 (FAIL)
  - [PASS] Playwright test discovery is tests/e2e: 16:  testDir: './tests/e2e', | cmd: `rg -n "testDir:\s*'./tests/e2e'" "/home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts"`
  - [FAIL] Playwright webServer uses backend :8000: error: Found argument '--port 8000' which wasn't expected, or isn't valid in this context

USAGE:
    
    rg [OPTIONS] PATTERN [PATH ...]
    rg [OPTIONS] -e PATTERN ... [PATH ...]
    rg [OPTIONS] -f PATTERNFILE ... [PATH ...]
    rg [OPTIONS] --files [PATH ...]
    rg [OPTIONS] --type-list
    command | rg [OPTIONS] PATTERN
    rg [OPTIONS] --help
    rg [OPTIONS] --version

For more information try --help | cmd: `rg -n "--port 8000" "/home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts"`
  - [FAIL] Frontend :8001 removed from default path: /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts:32:  // DB01: single unified backend on :8000 — :8001 legacy removed | cmd: `rg -n "8001" "/home/aarav/Aarav/Autopilot/autopilot-local/frontend"`
  - [PASS] CI starts backend before waiting health: workflow order is Start APEX backend -> Wait for APEX health
  - [PASS] Backend /health responds: status=healthy | cmd: `curl -sS -f http://127.0.0.1:8000/health`
  - [FAIL] Backend /api/health responds: HTTP returned JSON but missing expected status field | cmd: `curl -sS -f http://127.0.0.1:8000/api/health`
  - [FAIL] Frontend landing references /dashboard: unexpected pattern state | cmd: `rg -n "href="/dashboard"" "/home/aarav/Aarav/Autopilot/autopilot-local/frontend/app/page.tsx"`
  - [FAIL] Unified dev script references apex+web: /home/aarav/Aarav/Autopilot/autopilot-local/package.json:5:    "dev": "concurrently -n apex,web -c blue,green \"npm run dev:apex\" \"npm run dev:frontend\"", | cmd: `rg -n "dev": "concurrently -n apex,web" "/home/aarav/Aarav/Autopilot/autopilot-local/package.json"`
  - [FAIL] Day 003 singleton audit exists: missing /home/aarav/Aarav/Autopilot/docs/runtime/engine-singleton-audit.md
- Day 004 (FAIL)
  - [PASS] Playwright test discovery is tests/e2e: 16:  testDir: './tests/e2e', | cmd: `rg -n "testDir:\s*'./tests/e2e'" "/home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts"`
  - [FAIL] Playwright webServer uses backend :8000: error: Found argument '--port 8000' which wasn't expected, or isn't valid in this context

USAGE:
    
    rg [OPTIONS] PATTERN [PATH ...]
    rg [OPTIONS] -e PATTERN ... [PATH ...]
    rg [OPTIONS] -f PATTERNFILE ... [PATH ...]
    rg [OPTIONS] --files [PATH ...]
    rg [OPTIONS] --type-list
    command | rg [OPTIONS] PATTERN
    rg [OPTIONS] --help
    rg [OPTIONS] --version

For more information try --help | cmd: `rg -n "--port 8000" "/home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts"`
  - [FAIL] Frontend :8001 removed from default path: /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts:32:  // DB01: single unified backend on :8000 — :8001 legacy removed | cmd: `rg -n "8001" "/home/aarav/Aarav/Autopilot/autopilot-local/frontend"`
  - [PASS] CI starts backend before waiting health: workflow order is Start APEX backend -> Wait for APEX health
  - [PASS] Backend /health responds: status=healthy | cmd: `curl -sS -f http://127.0.0.1:8000/health`
  - [FAIL] Backend /api/health responds: HTTP returned JSON but missing expected status field | cmd: `curl -sS -f http://127.0.0.1:8000/api/health`
  - [FAIL] Frontend landing references /dashboard: unexpected pattern state | cmd: `rg -n "href="/dashboard"" "/home/aarav/Aarav/Autopilot/autopilot-local/frontend/app/page.tsx"`
  - [FAIL] Unified dev script references apex+web: /home/aarav/Aarav/Autopilot/autopilot-local/package.json:5:    "dev": "concurrently -n apex,web -c blue,green \"npm run dev:apex\" \"npm run dev:frontend\"", | cmd: `rg -n "dev": "concurrently -n apex,web" "/home/aarav/Aarav/Autopilot/autopilot-local/package.json"`
  - [FAIL] Day 004 scheduler registry doc exists: missing /home/aarav/Aarav/Autopilot/docs/scheduler/job-registry.md
- Day 005 (FAIL)
  - [PASS] Playwright test discovery is tests/e2e: 16:  testDir: './tests/e2e', | cmd: `rg -n "testDir:\s*'./tests/e2e'" "/home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts"`
  - [FAIL] Playwright webServer uses backend :8000: error: Found argument '--port 8000' which wasn't expected, or isn't valid in this context

USAGE:
    
    rg [OPTIONS] PATTERN [PATH ...]
    rg [OPTIONS] -e PATTERN ... [PATH ...]
    rg [OPTIONS] -f PATTERNFILE ... [PATH ...]
    rg [OPTIONS] --files [PATH ...]
    rg [OPTIONS] --type-list
    command | rg [OPTIONS] PATTERN
    rg [OPTIONS] --help
    rg [OPTIONS] --version

For more information try --help | cmd: `rg -n "--port 8000" "/home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts"`
  - [FAIL] Frontend :8001 removed from default path: /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts:32:  // DB01: single unified backend on :8000 — :8001 legacy removed | cmd: `rg -n "8001" "/home/aarav/Aarav/Autopilot/autopilot-local/frontend"`
  - [PASS] CI starts backend before waiting health: workflow order is Start APEX backend -> Wait for APEX health
  - [PASS] Backend /health responds: status=healthy | cmd: `curl -sS -f http://127.0.0.1:8000/health`
  - [FAIL] Backend /api/health responds: HTTP returned JSON but missing expected status field | cmd: `curl -sS -f http://127.0.0.1:8000/api/health`
  - [FAIL] Frontend landing references /dashboard: unexpected pattern state | cmd: `rg -n "href="/dashboard"" "/home/aarav/Aarav/Autopilot/autopilot-local/frontend/app/page.tsx"`
  - [FAIL] Unified dev script references apex+web: /home/aarav/Aarav/Autopilot/autopilot-local/package.json:5:    "dev": "concurrently -n apex,web -c blue,green \"npm run dev:apex\" \"npm run dev:frontend\"", | cmd: `rg -n "dev": "concurrently -n apex,web" "/home/aarav/Aarav/Autopilot/autopilot-local/package.json"`
  - [PASS] Day 005 CI workflow exists: found /home/aarav/Aarav/Autopilot/.github/workflows/ci.yml
- Day 006 (FAIL)
  - [PASS] Playwright test discovery is tests/e2e: 16:  testDir: './tests/e2e', | cmd: `rg -n "testDir:\s*'./tests/e2e'" "/home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts"`
  - [FAIL] Playwright webServer uses backend :8000: error: Found argument '--port 8000' which wasn't expected, or isn't valid in this context

USAGE:
    
    rg [OPTIONS] PATTERN [PATH ...]
    rg [OPTIONS] -e PATTERN ... [PATH ...]
    rg [OPTIONS] -f PATTERNFILE ... [PATH ...]
    rg [OPTIONS] --files [PATH ...]
    rg [OPTIONS] --type-list
    command | rg [OPTIONS] PATTERN
    rg [OPTIONS] --help
    rg [OPTIONS] --version

For more information try --help | cmd: `rg -n "--port 8000" "/home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts"`
  - [FAIL] Frontend :8001 removed from default path: /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts:32:  // DB01: single unified backend on :8000 — :8001 legacy removed | cmd: `rg -n "8001" "/home/aarav/Aarav/Autopilot/autopilot-local/frontend"`
  - [PASS] CI starts backend before waiting health: workflow order is Start APEX backend -> Wait for APEX health
  - [PASS] Backend /health responds: status=healthy | cmd: `curl -sS -f http://127.0.0.1:8000/health`
  - [FAIL] Backend /api/health responds: HTTP returned JSON but missing expected status field | cmd: `curl -sS -f http://127.0.0.1:8000/api/health`
  - [FAIL] Frontend landing references /dashboard: unexpected pattern state | cmd: `rg -n "href="/dashboard"" "/home/aarav/Aarav/Autopilot/autopilot-local/frontend/app/page.tsx"`
  - [FAIL] Unified dev script references apex+web: /home/aarav/Aarav/Autopilot/autopilot-local/package.json:5:    "dev": "concurrently -n apex,web -c blue,green \"npm run dev:apex\" \"npm run dev:frontend\"", | cmd: `rg -n "dev": "concurrently -n apex,web" "/home/aarav/Aarav/Autopilot/autopilot-local/package.json"`
  - [FAIL] Day 006 start-unified.sh exists: missing /home/aarav/Aarav/Autopilot/autopilot-local/start-unified.sh
- Day 007 (FAIL)
  - [PASS] Playwright test discovery is tests/e2e: 16:  testDir: './tests/e2e', | cmd: `rg -n "testDir:\s*'./tests/e2e'" "/home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts"`
  - [FAIL] Playwright webServer uses backend :8000: error: Found argument '--port 8000' which wasn't expected, or isn't valid in this context

USAGE:
    
    rg [OPTIONS] PATTERN [PATH ...]
    rg [OPTIONS] -e PATTERN ... [PATH ...]
    rg [OPTIONS] -f PATTERNFILE ... [PATH ...]
    rg [OPTIONS] --files [PATH ...]
    rg [OPTIONS] --type-list
    command | rg [OPTIONS] PATTERN
    rg [OPTIONS] --help
    rg [OPTIONS] --version

For more information try --help | cmd: `rg -n "--port 8000" "/home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts"`
  - [FAIL] Frontend :8001 removed from default path: /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts:32:  // DB01: single unified backend on :8000 — :8001 legacy removed | cmd: `rg -n "8001" "/home/aarav/Aarav/Autopilot/autopilot-local/frontend"`
  - [PASS] CI starts backend before waiting health: workflow order is Start APEX backend -> Wait for APEX health
  - [PASS] Backend /health responds: status=healthy | cmd: `curl -sS -f http://127.0.0.1:8000/health`
  - [FAIL] Backend /api/health responds: HTTP returned JSON but missing expected status field | cmd: `curl -sS -f http://127.0.0.1:8000/api/health`
  - [FAIL] Frontend landing references /dashboard: unexpected pattern state | cmd: `rg -n "href="/dashboard"" "/home/aarav/Aarav/Autopilot/autopilot-local/frontend/app/page.tsx"`
  - [FAIL] Unified dev script references apex+web: /home/aarav/Aarav/Autopilot/autopilot-local/package.json:5:    "dev": "concurrently -n apex,web -c blue,green \"npm run dev:apex\" \"npm run dev:frontend\"", | cmd: `rg -n "dev": "concurrently -n apex,web" "/home/aarav/Aarav/Autopilot/autopilot-local/package.json"`
  - [FAIL] Day 007 dev script is 2-process concurrently: /home/aarav/Aarav/Autopilot/autopilot-local/package.json:5:    "dev": "concurrently -n apex,web -c blue,green \"npm run dev:apex\" \"npm run dev:frontend\"", | cmd: `rg -n "dev": "concurrently -n apex,web -c blue,green" "/home/aarav/Aarav/Autopilot/autopilot-local/package.json"`
- Day 008 (FAIL)
  - [PASS] Playwright test discovery is tests/e2e: 16:  testDir: './tests/e2e', | cmd: `rg -n "testDir:\s*'./tests/e2e'" "/home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts"`
  - [FAIL] Playwright webServer uses backend :8000: error: Found argument '--port 8000' which wasn't expected, or isn't valid in this context

USAGE:
    
    rg [OPTIONS] PATTERN [PATH ...]
    rg [OPTIONS] -e PATTERN ... [PATH ...]
    rg [OPTIONS] -f PATTERNFILE ... [PATH ...]
    rg [OPTIONS] --files [PATH ...]
    rg [OPTIONS] --type-list
    command | rg [OPTIONS] PATTERN
    rg [OPTIONS] --help
    rg [OPTIONS] --version

For more information try --help | cmd: `rg -n "--port 8000" "/home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts"`
  - [FAIL] Frontend :8001 removed from default path: /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts:32:  // DB01: single unified backend on :8000 — :8001 legacy removed | cmd: `rg -n "8001" "/home/aarav/Aarav/Autopilot/autopilot-local/frontend"`
  - [PASS] CI starts backend before waiting health: workflow order is Start APEX backend -> Wait for APEX health
  - [PASS] Backend /health responds: status=healthy | cmd: `curl -sS -f http://127.0.0.1:8000/health`
  - [FAIL] Backend /api/health responds: HTTP returned JSON but missing expected status field | cmd: `curl -sS -f http://127.0.0.1:8000/api/health`
  - [FAIL] Frontend landing references /dashboard: unexpected pattern state | cmd: `rg -n "href="/dashboard"" "/home/aarav/Aarav/Autopilot/autopilot-local/frontend/app/page.tsx"`
  - [FAIL] Unified dev script references apex+web: /home/aarav/Aarav/Autopilot/autopilot-local/package.json:5:    "dev": "concurrently -n apex,web -c blue,green \"npm run dev:apex\" \"npm run dev:frontend\"", | cmd: `rg -n "dev": "concurrently -n apex,web" "/home/aarav/Aarav/Autopilot/autopilot-local/package.json"`
  - [FAIL] Day 008 start-unified.sh exists: missing /home/aarav/Aarav/Autopilot/autopilot-local/start-unified.sh
- Day 009 (FAIL)
  - [PASS] Playwright test discovery is tests/e2e: 16:  testDir: './tests/e2e', | cmd: `rg -n "testDir:\s*'./tests/e2e'" "/home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts"`
  - [FAIL] Playwright webServer uses backend :8000: error: Found argument '--port 8000' which wasn't expected, or isn't valid in this context

USAGE:
    
    rg [OPTIONS] PATTERN [PATH ...]
    rg [OPTIONS] -e PATTERN ... [PATH ...]
    rg [OPTIONS] -f PATTERNFILE ... [PATH ...]
    rg [OPTIONS] --files [PATH ...]
    rg [OPTIONS] --type-list
    command | rg [OPTIONS] PATTERN
    rg [OPTIONS] --help
    rg [OPTIONS] --version

For more information try --help | cmd: `rg -n "--port 8000" "/home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts"`
  - [FAIL] Frontend :8001 removed from default path: /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts:32:  // DB01: single unified backend on :8000 — :8001 legacy removed | cmd: `rg -n "8001" "/home/aarav/Aarav/Autopilot/autopilot-local/frontend"`
  - [PASS] CI starts backend before waiting health: workflow order is Start APEX backend -> Wait for APEX health
  - [PASS] Backend /health responds: status=healthy | cmd: `curl -sS -f http://127.0.0.1:8000/health`
  - [FAIL] Backend /api/health responds: HTTP returned JSON but missing expected status field | cmd: `curl -sS -f http://127.0.0.1:8000/api/health`
  - [FAIL] Frontend landing references /dashboard: unexpected pattern state | cmd: `rg -n "href="/dashboard"" "/home/aarav/Aarav/Autopilot/autopilot-local/frontend/app/page.tsx"`
  - [FAIL] Unified dev script references apex+web: /home/aarav/Aarav/Autopilot/autopilot-local/package.json:5:    "dev": "concurrently -n apex,web -c blue,green \"npm run dev:apex\" \"npm run dev:frontend\"", | cmd: `rg -n "dev": "concurrently -n apex,web" "/home/aarav/Aarav/Autopilot/autopilot-local/package.json"`
  - [FAIL] Day 009 start-unified.sh exists: missing /home/aarav/Aarav/Autopilot/autopilot-local/start-unified.sh
- Day 010 (FAIL)
  - [PASS] Playwright test discovery is tests/e2e: 16:  testDir: './tests/e2e', | cmd: `rg -n "testDir:\s*'./tests/e2e'" "/home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts"`
  - [FAIL] Playwright webServer uses backend :8000: error: Found argument '--port 8000' which wasn't expected, or isn't valid in this context

USAGE:
    
    rg [OPTIONS] PATTERN [PATH ...]
    rg [OPTIONS] -e PATTERN ... [PATH ...]
    rg [OPTIONS] -f PATTERNFILE ... [PATH ...]
    rg [OPTIONS] --files [PATH ...]
    rg [OPTIONS] --type-list
    command | rg [OPTIONS] PATTERN
    rg [OPTIONS] --help
    rg [OPTIONS] --version

For more information try --help | cmd: `rg -n "--port 8000" "/home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts"`
  - [FAIL] Frontend :8001 removed from default path: /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts:32:  // DB01: single unified backend on :8000 — :8001 legacy removed | cmd: `rg -n "8001" "/home/aarav/Aarav/Autopilot/autopilot-local/frontend"`
  - [PASS] CI starts backend before waiting health: workflow order is Start APEX backend -> Wait for APEX health
  - [PASS] Backend /health responds: status=healthy | cmd: `curl -sS -f http://127.0.0.1:8000/health`
  - [FAIL] Backend /api/health responds: HTTP returned JSON but missing expected status field | cmd: `curl -sS -f http://127.0.0.1:8000/api/health`
  - [FAIL] Frontend landing references /dashboard: unexpected pattern state | cmd: `rg -n "href="/dashboard"" "/home/aarav/Aarav/Autopilot/autopilot-local/frontend/app/page.tsx"`
  - [FAIL] Unified dev script references apex+web: /home/aarav/Aarav/Autopilot/autopilot-local/package.json:5:    "dev": "concurrently -n apex,web -c blue,green \"npm run dev:apex\" \"npm run dev:frontend\"", | cmd: `rg -n "dev": "concurrently -n apex,web" "/home/aarav/Aarav/Autopilot/autopilot-local/package.json"`
  - [FAIL] Day 010 start-unified.sh exists: missing /home/aarav/Aarav/Autopilot/autopilot-local/start-unified.sh

### Day 2-10 Verification Harness Results

- Timestamp: 2026-05-27T13:48:27.407222+00:00
- Runner: `python scripts/verification/verify_days_002_010.py --days 2-10`

| Day | Status | Deliverable |
|---|---|---|
| 002 | FAIL | PR checklist: Playwright single `:8000` webServer + `.env.local.example` (verification) |
| 003 | FAIL | docs/runtime/engine-singleton-audit.md — no hot-path `build_engine()` (verification) |
| 004 | FAIL | docs/scheduler/job-registry.md — APScheduler idempotency sign-off (verification) |
| 005 | FAIL | CI green: `.github/workflows/ci.yml` + Playwright webServer only (verification) |
| 006 | FAIL | Verify `start-unified.sh` health-wait on `:8000` — no `:8001` in default path |
| 007 | FAIL | Verify `package.json` dev script = apex + frontend only (2 processes) |
| 008 | FAIL | Verify pid/log rotation in start-unified.sh |
| 009 | FAIL | Verify graceful stop kills only unified backend |
| 010 | FAIL | DB02 EXIT: operator path never starts `:8001` (verification sign-off) |

#### Evidence
- Day 002 (FAIL)
  - [PASS] Playwright test discovery is tests/e2e: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts
  - [PASS] Playwright webServer uses backend :8000: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts
  - [FAIL] Frontend :8001 removed from default path: /home/aarav/Aarav/Autopilot/autopilot-local/frontend/tests/e2e/full-terminal.spec.ts:232:      if ((u.includes(':8000') || u.includes(':8001')) && res.status() >= 400) { | cmd: `rg -n '8001' '/home/aarav/Aarav/Autopilot/autopilot-local/frontend'`
  - [PASS] CI starts backend before waiting health: workflow order is Start APEX backend -> Wait for APEX health
  - [PASS] Backend /health responds: status=healthy | cmd: `curl -sS -f http://127.0.0.1:8000/health`
  - [PASS] Backend /api/health responds: contains engine + alpaca payload | cmd: `curl -sS -f http://127.0.0.1:8000/api/health`
  - [PASS] Frontend landing references /dashboard: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/app/page.tsx
  - [PASS] Unified dev script references apex+web: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/package.json
  - [PASS] Day 002 .env.local.example exists: found /home/aarav/Aarav/Autopilot/autopilot-local/.env.local.example
- Day 003 (FAIL)
  - [PASS] Playwright test discovery is tests/e2e: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts
  - [PASS] Playwright webServer uses backend :8000: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts
  - [FAIL] Frontend :8001 removed from default path: /home/aarav/Aarav/Autopilot/autopilot-local/frontend/tests/e2e/full-terminal.spec.ts:232:      if ((u.includes(':8000') || u.includes(':8001')) && res.status() >= 400) { | cmd: `rg -n '8001' '/home/aarav/Aarav/Autopilot/autopilot-local/frontend'`
  - [PASS] CI starts backend before waiting health: workflow order is Start APEX backend -> Wait for APEX health
  - [PASS] Backend /health responds: status=healthy | cmd: `curl -sS -f http://127.0.0.1:8000/health`
  - [PASS] Backend /api/health responds: contains engine + alpaca payload | cmd: `curl -sS -f http://127.0.0.1:8000/api/health`
  - [PASS] Frontend landing references /dashboard: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/app/page.tsx
  - [PASS] Unified dev script references apex+web: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/package.json
  - [FAIL] Day 003 singleton audit exists: missing /home/aarav/Aarav/Autopilot/docs/runtime/engine-singleton-audit.md
- Day 004 (FAIL)
  - [PASS] Playwright test discovery is tests/e2e: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts
  - [PASS] Playwright webServer uses backend :8000: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts
  - [FAIL] Frontend :8001 removed from default path: /home/aarav/Aarav/Autopilot/autopilot-local/frontend/tests/e2e/full-terminal.spec.ts:232:      if ((u.includes(':8000') || u.includes(':8001')) && res.status() >= 400) { | cmd: `rg -n '8001' '/home/aarav/Aarav/Autopilot/autopilot-local/frontend'`
  - [PASS] CI starts backend before waiting health: workflow order is Start APEX backend -> Wait for APEX health
  - [PASS] Backend /health responds: status=healthy | cmd: `curl -sS -f http://127.0.0.1:8000/health`
  - [PASS] Backend /api/health responds: contains engine + alpaca payload | cmd: `curl -sS -f http://127.0.0.1:8000/api/health`
  - [PASS] Frontend landing references /dashboard: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/app/page.tsx
  - [PASS] Unified dev script references apex+web: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/package.json
  - [FAIL] Day 004 scheduler registry doc exists: missing /home/aarav/Aarav/Autopilot/docs/scheduler/job-registry.md
- Day 005 (FAIL)
  - [PASS] Playwright test discovery is tests/e2e: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts
  - [PASS] Playwright webServer uses backend :8000: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts
  - [FAIL] Frontend :8001 removed from default path: /home/aarav/Aarav/Autopilot/autopilot-local/frontend/tests/e2e/full-terminal.spec.ts:232:      if ((u.includes(':8000') || u.includes(':8001')) && res.status() >= 400) { | cmd: `rg -n '8001' '/home/aarav/Aarav/Autopilot/autopilot-local/frontend'`
  - [PASS] CI starts backend before waiting health: workflow order is Start APEX backend -> Wait for APEX health
  - [PASS] Backend /health responds: status=healthy | cmd: `curl -sS -f http://127.0.0.1:8000/health`
  - [PASS] Backend /api/health responds: contains engine + alpaca payload | cmd: `curl -sS -f http://127.0.0.1:8000/api/health`
  - [PASS] Frontend landing references /dashboard: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/app/page.tsx
  - [PASS] Unified dev script references apex+web: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/package.json
  - [PASS] Day 005 CI workflow exists: found /home/aarav/Aarav/Autopilot/.github/workflows/ci.yml
- Day 006 (FAIL)
  - [PASS] Playwright test discovery is tests/e2e: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts
  - [PASS] Playwright webServer uses backend :8000: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts
  - [FAIL] Frontend :8001 removed from default path: /home/aarav/Aarav/Autopilot/autopilot-local/frontend/tests/e2e/full-terminal.spec.ts:232:      if ((u.includes(':8000') || u.includes(':8001')) && res.status() >= 400) { | cmd: `rg -n '8001' '/home/aarav/Aarav/Autopilot/autopilot-local/frontend'`
  - [PASS] CI starts backend before waiting health: workflow order is Start APEX backend -> Wait for APEX health
  - [PASS] Backend /health responds: status=healthy | cmd: `curl -sS -f http://127.0.0.1:8000/health`
  - [PASS] Backend /api/health responds: contains engine + alpaca payload | cmd: `curl -sS -f http://127.0.0.1:8000/api/health`
  - [PASS] Frontend landing references /dashboard: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/app/page.tsx
  - [PASS] Unified dev script references apex+web: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/package.json
  - [FAIL] Day 006 start-unified.sh exists: missing /home/aarav/Aarav/Autopilot/autopilot-local/start-unified.sh
- Day 007 (FAIL)
  - [PASS] Playwright test discovery is tests/e2e: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts
  - [PASS] Playwright webServer uses backend :8000: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts
  - [FAIL] Frontend :8001 removed from default path: /home/aarav/Aarav/Autopilot/autopilot-local/frontend/tests/e2e/full-terminal.spec.ts:232:      if ((u.includes(':8000') || u.includes(':8001')) && res.status() >= 400) { | cmd: `rg -n '8001' '/home/aarav/Aarav/Autopilot/autopilot-local/frontend'`
  - [PASS] CI starts backend before waiting health: workflow order is Start APEX backend -> Wait for APEX health
  - [PASS] Backend /health responds: status=healthy | cmd: `curl -sS -f http://127.0.0.1:8000/health`
  - [PASS] Backend /api/health responds: contains engine + alpaca payload | cmd: `curl -sS -f http://127.0.0.1:8000/api/health`
  - [PASS] Frontend landing references /dashboard: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/app/page.tsx
  - [PASS] Unified dev script references apex+web: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/package.json
  - [PASS] Day 007 dev script is 2-process concurrently: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/package.json
- Day 008 (FAIL)
  - [PASS] Playwright test discovery is tests/e2e: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts
  - [PASS] Playwright webServer uses backend :8000: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts
  - [FAIL] Frontend :8001 removed from default path: /home/aarav/Aarav/Autopilot/autopilot-local/frontend/tests/e2e/full-terminal.spec.ts:232:      if ((u.includes(':8000') || u.includes(':8001')) && res.status() >= 400) { | cmd: `rg -n '8001' '/home/aarav/Aarav/Autopilot/autopilot-local/frontend'`
  - [PASS] CI starts backend before waiting health: workflow order is Start APEX backend -> Wait for APEX health
  - [PASS] Backend /health responds: status=healthy | cmd: `curl -sS -f http://127.0.0.1:8000/health`
  - [PASS] Backend /api/health responds: contains engine + alpaca payload | cmd: `curl -sS -f http://127.0.0.1:8000/api/health`
  - [PASS] Frontend landing references /dashboard: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/app/page.tsx
  - [PASS] Unified dev script references apex+web: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/package.json
  - [FAIL] Day 008 start-unified.sh exists: missing /home/aarav/Aarav/Autopilot/autopilot-local/start-unified.sh
- Day 009 (FAIL)
  - [PASS] Playwright test discovery is tests/e2e: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts
  - [PASS] Playwright webServer uses backend :8000: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts
  - [FAIL] Frontend :8001 removed from default path: /home/aarav/Aarav/Autopilot/autopilot-local/frontend/tests/e2e/full-terminal.spec.ts:232:      if ((u.includes(':8000') || u.includes(':8001')) && res.status() >= 400) { | cmd: `rg -n '8001' '/home/aarav/Aarav/Autopilot/autopilot-local/frontend'`
  - [PASS] CI starts backend before waiting health: workflow order is Start APEX backend -> Wait for APEX health
  - [PASS] Backend /health responds: status=healthy | cmd: `curl -sS -f http://127.0.0.1:8000/health`
  - [PASS] Backend /api/health responds: contains engine + alpaca payload | cmd: `curl -sS -f http://127.0.0.1:8000/api/health`
  - [PASS] Frontend landing references /dashboard: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/app/page.tsx
  - [PASS] Unified dev script references apex+web: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/package.json
  - [FAIL] Day 009 start-unified.sh exists: missing /home/aarav/Aarav/Autopilot/autopilot-local/start-unified.sh
- Day 010 (FAIL)
  - [PASS] Playwright test discovery is tests/e2e: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts
  - [PASS] Playwright webServer uses backend :8000: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts
  - [FAIL] Frontend :8001 removed from default path: /home/aarav/Aarav/Autopilot/autopilot-local/frontend/tests/e2e/full-terminal.spec.ts:232:      if ((u.includes(':8000') || u.includes(':8001')) && res.status() >= 400) { | cmd: `rg -n '8001' '/home/aarav/Aarav/Autopilot/autopilot-local/frontend'`
  - [PASS] CI starts backend before waiting health: workflow order is Start APEX backend -> Wait for APEX health
  - [PASS] Backend /health responds: status=healthy | cmd: `curl -sS -f http://127.0.0.1:8000/health`
  - [PASS] Backend /api/health responds: contains engine + alpaca payload | cmd: `curl -sS -f http://127.0.0.1:8000/api/health`
  - [PASS] Frontend landing references /dashboard: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/app/page.tsx
  - [PASS] Unified dev script references apex+web: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/package.json
  - [FAIL] Day 010 start-unified.sh exists: missing /home/aarav/Aarav/Autopilot/autopilot-local/start-unified.sh

### Day 2-10 Verification Harness Results

- Timestamp: 2026-05-27T13:57:57.473649+00:00
- Runner: `python scripts/verification/verify_days_002_010.py --days 2-10`

| Day | Status | Deliverable |
|---|---|---|
| 002 | PASS | PR checklist: Playwright single `:8000` webServer + `.env.local.example` (verification) |
| 003 | PASS | docs/runtime/engine-singleton-audit.md — no hot-path `build_engine()` (verification) |
| 004 | PASS | docs/scheduler/job-registry.md — APScheduler idempotency sign-off (verification) |
| 005 | PASS | CI green: `.github/workflows/ci.yml` + Playwright webServer only (verification) |
| 006 | PASS | Verify `start-unified.sh` health-wait on `:8000` — no `:8001` in default path |
| 007 | PASS | Verify `package.json` dev script = apex + frontend only (2 processes) |
| 008 | PASS | Verify pid/log rotation in start-unified.sh |
| 009 | PASS | Verify graceful stop kills only unified backend |
| 010 | PASS | DB02 EXIT: operator path never starts `:8001` (verification sign-off) |

#### Evidence
- Day 002 (PASS)
  - [PASS] Playwright test discovery is tests/e2e: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts
  - [PASS] Playwright webServer uses backend :8000: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts
  - [PASS] Frontend :8001 removed from default path: only comment/reference mentions found | cmd: `rg -n '8001' '/home/aarav/Aarav/Autopilot/autopilot-local/frontend'`
  - [PASS] CI starts backend before waiting health: workflow order is Start APEX backend -> Wait for APEX health
  - [PASS] Backend /health responds: status=healthy | cmd: `curl -sS -f http://127.0.0.1:8000/health`
  - [PASS] Backend /api/health responds: contains engine + alpaca payload | cmd: `curl -sS -f http://127.0.0.1:8000/api/health`
  - [PASS] Frontend landing references /dashboard: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/app/page.tsx
  - [PASS] Unified dev script references apex+web: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/package.json
  - [PASS] Day 002 .env.local.example exists: found /home/aarav/Aarav/Autopilot/autopilot-local/.env.local.example
- Day 003 (PASS)
  - [PASS] Playwright test discovery is tests/e2e: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts
  - [PASS] Playwright webServer uses backend :8000: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts
  - [PASS] Frontend :8001 removed from default path: only comment/reference mentions found | cmd: `rg -n '8001' '/home/aarav/Aarav/Autopilot/autopilot-local/frontend'`
  - [PASS] CI starts backend before waiting health: workflow order is Start APEX backend -> Wait for APEX health
  - [PASS] Backend /health responds: status=healthy | cmd: `curl -sS -f http://127.0.0.1:8000/health`
  - [PASS] Backend /api/health responds: contains engine + alpaca payload | cmd: `curl -sS -f http://127.0.0.1:8000/api/health`
  - [PASS] Frontend landing references /dashboard: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/app/page.tsx
  - [PASS] Unified dev script references apex+web: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/package.json
  - [PASS] Day 003 audit references build_engine(): pattern found in /home/aarav/Aarav/Autopilot/docs/runtime/engine-singleton-audit.md
- Day 004 (PASS)
  - [PASS] Playwright test discovery is tests/e2e: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts
  - [PASS] Playwright webServer uses backend :8000: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts
  - [PASS] Frontend :8001 removed from default path: only comment/reference mentions found | cmd: `rg -n '8001' '/home/aarav/Aarav/Autopilot/autopilot-local/frontend'`
  - [PASS] CI starts backend before waiting health: workflow order is Start APEX backend -> Wait for APEX health
  - [PASS] Backend /health responds: status=healthy | cmd: `curl -sS -f http://127.0.0.1:8000/health`
  - [PASS] Backend /api/health responds: contains engine + alpaca payload | cmd: `curl -sS -f http://127.0.0.1:8000/api/health`
  - [PASS] Frontend landing references /dashboard: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/app/page.tsx
  - [PASS] Unified dev script references apex+web: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/package.json
  - [PASS] Day 004 scheduler registry doc exists: found /home/aarav/Aarav/Autopilot/docs/scheduler/job-registry.md
- Day 005 (PASS)
  - [PASS] Playwright test discovery is tests/e2e: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts
  - [PASS] Playwright webServer uses backend :8000: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts
  - [PASS] Frontend :8001 removed from default path: only comment/reference mentions found | cmd: `rg -n '8001' '/home/aarav/Aarav/Autopilot/autopilot-local/frontend'`
  - [PASS] CI starts backend before waiting health: workflow order is Start APEX backend -> Wait for APEX health
  - [PASS] Backend /health responds: status=healthy | cmd: `curl -sS -f http://127.0.0.1:8000/health`
  - [PASS] Backend /api/health responds: contains engine + alpaca payload | cmd: `curl -sS -f http://127.0.0.1:8000/api/health`
  - [PASS] Frontend landing references /dashboard: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/app/page.tsx
  - [PASS] Unified dev script references apex+web: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/package.json
  - [PASS] Day 005 CI workflow exists: found /home/aarav/Aarav/Autopilot/.github/workflows/ci.yml
- Day 006 (PASS)
  - [PASS] Playwright test discovery is tests/e2e: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts
  - [PASS] Playwright webServer uses backend :8000: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts
  - [PASS] Frontend :8001 removed from default path: only comment/reference mentions found | cmd: `rg -n '8001' '/home/aarav/Aarav/Autopilot/autopilot-local/frontend'`
  - [PASS] CI starts backend before waiting health: workflow order is Start APEX backend -> Wait for APEX health
  - [PASS] Backend /health responds: status=healthy | cmd: `curl -sS -f http://127.0.0.1:8000/health`
  - [PASS] Backend /api/health responds: contains engine + alpaca payload | cmd: `curl -sS -f http://127.0.0.1:8000/api/health`
  - [PASS] Frontend landing references /dashboard: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/app/page.tsx
  - [PASS] Unified dev script references apex+web: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/package.json
  - [PASS] Day 006 start-unified.sh exists: found /home/aarav/Aarav/Autopilot/autopilot-local/start-unified.sh
- Day 007 (PASS)
  - [PASS] Playwright test discovery is tests/e2e: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts
  - [PASS] Playwright webServer uses backend :8000: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts
  - [PASS] Frontend :8001 removed from default path: only comment/reference mentions found | cmd: `rg -n '8001' '/home/aarav/Aarav/Autopilot/autopilot-local/frontend'`
  - [PASS] CI starts backend before waiting health: workflow order is Start APEX backend -> Wait for APEX health
  - [PASS] Backend /health responds: status=healthy | cmd: `curl -sS -f http://127.0.0.1:8000/health`
  - [PASS] Backend /api/health responds: contains engine + alpaca payload | cmd: `curl -sS -f http://127.0.0.1:8000/api/health`
  - [PASS] Frontend landing references /dashboard: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/app/page.tsx
  - [PASS] Unified dev script references apex+web: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/package.json
  - [PASS] Day 007 dev script is 2-process concurrently: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/package.json
- Day 008 (PASS)
  - [PASS] Playwright test discovery is tests/e2e: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts
  - [PASS] Playwright webServer uses backend :8000: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts
  - [PASS] Frontend :8001 removed from default path: only comment/reference mentions found | cmd: `rg -n '8001' '/home/aarav/Aarav/Autopilot/autopilot-local/frontend'`
  - [PASS] CI starts backend before waiting health: workflow order is Start APEX backend -> Wait for APEX health
  - [PASS] Backend /health responds: status=healthy | cmd: `curl -sS -f http://127.0.0.1:8000/health`
  - [PASS] Backend /api/health responds: contains engine + alpaca payload | cmd: `curl -sS -f http://127.0.0.1:8000/api/health`
  - [PASS] Frontend landing references /dashboard: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/app/page.tsx
  - [PASS] Unified dev script references apex+web: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/package.json
  - [PASS] Day 008 start-unified.sh exists: found /home/aarav/Aarav/Autopilot/autopilot-local/start-unified.sh
- Day 009 (PASS)
  - [PASS] Playwright test discovery is tests/e2e: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts
  - [PASS] Playwright webServer uses backend :8000: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts
  - [PASS] Frontend :8001 removed from default path: only comment/reference mentions found | cmd: `rg -n '8001' '/home/aarav/Aarav/Autopilot/autopilot-local/frontend'`
  - [PASS] CI starts backend before waiting health: workflow order is Start APEX backend -> Wait for APEX health
  - [PASS] Backend /health responds: status=healthy | cmd: `curl -sS -f http://127.0.0.1:8000/health`
  - [PASS] Backend /api/health responds: contains engine + alpaca payload | cmd: `curl -sS -f http://127.0.0.1:8000/api/health`
  - [PASS] Frontend landing references /dashboard: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/app/page.tsx
  - [PASS] Unified dev script references apex+web: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/package.json
  - [PASS] Day 009 start-unified.sh exists: found /home/aarav/Aarav/Autopilot/autopilot-local/start-unified.sh
- Day 010 (PASS)
  - [PASS] Playwright test discovery is tests/e2e: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts
  - [PASS] Playwright webServer uses backend :8000: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts
  - [PASS] Frontend :8001 removed from default path: only comment/reference mentions found | cmd: `rg -n '8001' '/home/aarav/Aarav/Autopilot/autopilot-local/frontend'`
  - [PASS] CI starts backend before waiting health: workflow order is Start APEX backend -> Wait for APEX health
  - [PASS] Backend /health responds: status=healthy | cmd: `curl -sS -f http://127.0.0.1:8000/health`
  - [PASS] Backend /api/health responds: contains engine + alpaca payload | cmd: `curl -sS -f http://127.0.0.1:8000/api/health`
  - [PASS] Frontend landing references /dashboard: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/app/page.tsx
  - [PASS] Unified dev script references apex+web: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/package.json
  - [PASS] Day 010 start-unified.sh exists: found /home/aarav/Aarav/Autopilot/autopilot-local/start-unified.sh

### Day 2-10 Verification Harness Results

- Timestamp: 2026-05-27T18:36:33.581853+00:00
- Runner: `python scripts/verification/verify_days_002_010.py --days 2-10`

| Day | Status | Deliverable |
|---|---|---|
| 002 | PASS | PR checklist: Playwright single `:8000` webServer + `.env.local.example` (verification) |
| 003 | PASS | docs/runtime/engine-singleton-audit.md — no hot-path `build_engine()` (verification) |
| 004 | PASS | docs/scheduler/job-registry.md — APScheduler idempotency sign-off (verification) |
| 005 | PASS | CI green: `.github/workflows/ci.yml` + Playwright webServer only (verification) |
| 006 | PASS | Verify `start-unified.sh` health-wait on `:8000` — no `:8001` in default path |
| 007 | PASS | Verify `package.json` dev script = apex + frontend only (2 processes) |
| 008 | PASS | Verify pid/log rotation in start-unified.sh |
| 009 | PASS | Verify graceful stop kills only unified backend |
| 010 | PASS | DB02 EXIT: operator path never starts `:8001` (verification sign-off) |

#### Evidence
- Day 002 (PASS)
  - [PASS] Playwright test discovery is tests/e2e: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts
  - [PASS] Playwright webServer uses backend :8000: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts
  - [PASS] Frontend :8001 removed from default path: only comment/reference mentions found | cmd: `rg -n '8001' '/home/aarav/Aarav/Autopilot/autopilot-local/frontend'`
  - [PASS] CI starts backend before waiting health: workflow order is Start APEX backend -> Wait for APEX health
  - [PASS] Backend /health responds: status=healthy | cmd: `curl -sS -f http://127.0.0.1:8000/health`
  - [PASS] Backend /api/health responds: contains engine + alpaca payload | cmd: `curl -sS -f http://127.0.0.1:8000/api/health`
  - [PASS] Frontend landing references /dashboard: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/app/page.tsx
  - [PASS] Unified dev script references apex+web: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/package.json
  - [PASS] Day 002 .env.local.example exists: found /home/aarav/Aarav/Autopilot/autopilot-local/.env.local.example
- Day 003 (PASS)
  - [PASS] Playwright test discovery is tests/e2e: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts
  - [PASS] Playwright webServer uses backend :8000: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts
  - [PASS] Frontend :8001 removed from default path: only comment/reference mentions found | cmd: `rg -n '8001' '/home/aarav/Aarav/Autopilot/autopilot-local/frontend'`
  - [PASS] CI starts backend before waiting health: workflow order is Start APEX backend -> Wait for APEX health
  - [PASS] Backend /health responds: status=healthy | cmd: `curl -sS -f http://127.0.0.1:8000/health`
  - [PASS] Backend /api/health responds: contains engine + alpaca payload | cmd: `curl -sS -f http://127.0.0.1:8000/api/health`
  - [PASS] Frontend landing references /dashboard: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/app/page.tsx
  - [PASS] Unified dev script references apex+web: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/package.json
  - [PASS] Day 003 audit references build_engine(): pattern found in /home/aarav/Aarav/Autopilot/docs/runtime/engine-singleton-audit.md
- Day 004 (PASS)
  - [PASS] Playwright test discovery is tests/e2e: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts
  - [PASS] Playwright webServer uses backend :8000: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts
  - [PASS] Frontend :8001 removed from default path: only comment/reference mentions found | cmd: `rg -n '8001' '/home/aarav/Aarav/Autopilot/autopilot-local/frontend'`
  - [PASS] CI starts backend before waiting health: workflow order is Start APEX backend -> Wait for APEX health
  - [PASS] Backend /health responds: status=healthy | cmd: `curl -sS -f http://127.0.0.1:8000/health`
  - [PASS] Backend /api/health responds: contains engine + alpaca payload | cmd: `curl -sS -f http://127.0.0.1:8000/api/health`
  - [PASS] Frontend landing references /dashboard: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/app/page.tsx
  - [PASS] Unified dev script references apex+web: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/package.json
  - [PASS] Day 004 scheduler registry doc exists: found /home/aarav/Aarav/Autopilot/docs/scheduler/job-registry.md
- Day 005 (PASS)
  - [PASS] Playwright test discovery is tests/e2e: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts
  - [PASS] Playwright webServer uses backend :8000: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts
  - [PASS] Frontend :8001 removed from default path: only comment/reference mentions found | cmd: `rg -n '8001' '/home/aarav/Aarav/Autopilot/autopilot-local/frontend'`
  - [PASS] CI starts backend before waiting health: workflow order is Start APEX backend -> Wait for APEX health
  - [PASS] Backend /health responds: status=healthy | cmd: `curl -sS -f http://127.0.0.1:8000/health`
  - [PASS] Backend /api/health responds: contains engine + alpaca payload | cmd: `curl -sS -f http://127.0.0.1:8000/api/health`
  - [PASS] Frontend landing references /dashboard: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/app/page.tsx
  - [PASS] Unified dev script references apex+web: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/package.json
  - [PASS] Day 005 CI workflow exists: found /home/aarav/Aarav/Autopilot/.github/workflows/ci.yml
- Day 006 (PASS)
  - [PASS] Playwright test discovery is tests/e2e: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts
  - [PASS] Playwright webServer uses backend :8000: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts
  - [PASS] Frontend :8001 removed from default path: only comment/reference mentions found | cmd: `rg -n '8001' '/home/aarav/Aarav/Autopilot/autopilot-local/frontend'`
  - [PASS] CI starts backend before waiting health: workflow order is Start APEX backend -> Wait for APEX health
  - [PASS] Backend /health responds: status=healthy | cmd: `curl -sS -f http://127.0.0.1:8000/health`
  - [PASS] Backend /api/health responds: contains engine + alpaca payload | cmd: `curl -sS -f http://127.0.0.1:8000/api/health`
  - [PASS] Frontend landing references /dashboard: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/app/page.tsx
  - [PASS] Unified dev script references apex+web: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/package.json
  - [PASS] Day 006 start-unified.sh exists: found /home/aarav/Aarav/Autopilot/autopilot-local/start-unified.sh
- Day 007 (PASS)
  - [PASS] Playwright test discovery is tests/e2e: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts
  - [PASS] Playwright webServer uses backend :8000: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts
  - [PASS] Frontend :8001 removed from default path: only comment/reference mentions found | cmd: `rg -n '8001' '/home/aarav/Aarav/Autopilot/autopilot-local/frontend'`
  - [PASS] CI starts backend before waiting health: workflow order is Start APEX backend -> Wait for APEX health
  - [PASS] Backend /health responds: status=healthy | cmd: `curl -sS -f http://127.0.0.1:8000/health`
  - [PASS] Backend /api/health responds: contains engine + alpaca payload | cmd: `curl -sS -f http://127.0.0.1:8000/api/health`
  - [PASS] Frontend landing references /dashboard: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/app/page.tsx
  - [PASS] Unified dev script references apex+web: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/package.json
  - [PASS] Day 007 dev script is 2-process concurrently: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/package.json
- Day 008 (PASS)
  - [PASS] Playwright test discovery is tests/e2e: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts
  - [PASS] Playwright webServer uses backend :8000: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts
  - [PASS] Frontend :8001 removed from default path: only comment/reference mentions found | cmd: `rg -n '8001' '/home/aarav/Aarav/Autopilot/autopilot-local/frontend'`
  - [PASS] CI starts backend before waiting health: workflow order is Start APEX backend -> Wait for APEX health
  - [PASS] Backend /health responds: status=healthy | cmd: `curl -sS -f http://127.0.0.1:8000/health`
  - [PASS] Backend /api/health responds: contains engine + alpaca payload | cmd: `curl -sS -f http://127.0.0.1:8000/api/health`
  - [PASS] Frontend landing references /dashboard: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/app/page.tsx
  - [PASS] Unified dev script references apex+web: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/package.json
  - [PASS] Day 008 start-unified.sh exists: found /home/aarav/Aarav/Autopilot/autopilot-local/start-unified.sh
- Day 009 (PASS)
  - [PASS] Playwright test discovery is tests/e2e: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts
  - [PASS] Playwright webServer uses backend :8000: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts
  - [PASS] Frontend :8001 removed from default path: only comment/reference mentions found | cmd: `rg -n '8001' '/home/aarav/Aarav/Autopilot/autopilot-local/frontend'`
  - [PASS] CI starts backend before waiting health: workflow order is Start APEX backend -> Wait for APEX health
  - [PASS] Backend /health responds: status=healthy | cmd: `curl -sS -f http://127.0.0.1:8000/health`
  - [PASS] Backend /api/health responds: contains engine + alpaca payload | cmd: `curl -sS -f http://127.0.0.1:8000/api/health`
  - [PASS] Frontend landing references /dashboard: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/app/page.tsx
  - [PASS] Unified dev script references apex+web: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/package.json
  - [PASS] Day 009 start-unified.sh exists: found /home/aarav/Aarav/Autopilot/autopilot-local/start-unified.sh
- Day 010 (PASS)
  - [PASS] Playwright test discovery is tests/e2e: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts
  - [PASS] Playwright webServer uses backend :8000: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/playwright.config.ts
  - [PASS] Frontend :8001 removed from default path: only comment/reference mentions found | cmd: `rg -n '8001' '/home/aarav/Aarav/Autopilot/autopilot-local/frontend'`
  - [PASS] CI starts backend before waiting health: workflow order is Start APEX backend -> Wait for APEX health
  - [PASS] Backend /health responds: status=healthy | cmd: `curl -sS -f http://127.0.0.1:8000/health`
  - [PASS] Backend /api/health responds: contains engine + alpaca payload | cmd: `curl -sS -f http://127.0.0.1:8000/api/health`
  - [PASS] Frontend landing references /dashboard: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/frontend/app/page.tsx
  - [PASS] Unified dev script references apex+web: pattern found in /home/aarav/Aarav/Autopilot/autopilot-local/package.json
  - [PASS] Day 010 start-unified.sh exists: found /home/aarav/Aarav/Autopilot/autopilot-local/start-unified.sh
