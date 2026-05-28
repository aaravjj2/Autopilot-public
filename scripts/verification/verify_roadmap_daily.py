#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

REQUIRED_HEADERS = (
    "## Outcome Target",
    "## Preconditions",
    "## Work Packages",
    "## End-of-Day Verification Matrix",
    "## Daily Changelog Template",
)

FORBIDDEN_PATTERNS = (
    r"\bTODO\b",
    r"\bTBD\b",
    r"<placeholder>",
    r"\bXXX\b",
    r"lorem ipsum",
)


def verify_file(path: Path, min_lines: int) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if len(lines) < min_lines:
        errors.append(f"line_count<{min_lines} ({len(lines)})")

    for header in REQUIRED_HEADERS:
        if header not in text:
            errors.append(f"missing_header:{header}")

    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            errors.append(f"forbidden_token:{pattern}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate day-NNN roadmap markdown files.")
    parser.add_argument("--dir", default="one-year-daily", help="Directory containing day-*.md")
    parser.add_argument("--start", type=int, default=1, help="Starting day number inclusive")
    parser.add_argument("--end", type=int, default=60, help="Ending day number inclusive")
    parser.add_argument("--min-lines", type=int, default=350, help="Minimum required line count")
    args = parser.parse_args()

    root = Path(args.dir)
    if not root.exists():
        print(f"FAIL: directory not found: {root}")
        return 1

    failures = 0
    checked = 0
    for day in range(args.start, args.end + 1):
        path = root / f"day-{day:03d}.md"
        if not path.exists():
            print(f"FAIL day-{day:03d}: file_missing")
            failures += 1
            continue
        checked += 1
        errs = verify_file(path, args.min_lines)
        if errs:
            print(f"FAIL day-{day:03d}: {', '.join(errs)}")
            failures += 1
        else:
            print(f"PASS day-{day:03d}")

    print(f"\nChecked: {checked} files | Failures: {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

