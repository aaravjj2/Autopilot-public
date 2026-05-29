#!/usr/bin/env python3
"""Extract a single key's raw value from a .env file and print it to stdout.

Handles single-line values and multiline double-quoted values (e.g. PEM keys).
Prints nothing (exit 0) if the key is absent or empty. Never logs anything else,
so it is safe to use inside a deploy pipeline without leaking other secrets.
"""
from __future__ import annotations

import sys


def read_value(path: str, key: str) -> str | None:
    with open(path, encoding="utf-8") as fh:
        lines = fh.readlines()

    prefix = f"{key}="
    i = 0
    n = len(lines)
    while i < n:
        raw = lines[i].rstrip("\n")
        stripped = raw.lstrip()
        if stripped.startswith("#") or "=" not in stripped:
            i += 1
            continue
        # Match KEY= possibly with surrounding spaces (e.g. "BRIGHTDATA_API_KEY =")
        name, _, rest = raw.partition("=")
        if name.strip() != key:
            i += 1
            continue
        val = rest
        # Multiline double-quoted value
        if val.lstrip().startswith('"') and val.count('"') < 2:
            collected = [val.lstrip()[1:]]  # drop opening quote
            i += 1
            while i < n:
                cur = lines[i].rstrip("\n")
                if '"' in cur:
                    collected.append(cur[: cur.index('"')])
                    break
                collected.append(cur)
                i += 1
            return "\n".join(collected)
        # Single-line value: strip matching surrounding quotes
        val = val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
            val = val[1:-1]
        return val
    return None


def main() -> int:
    if len(sys.argv) != 3:
        return 2
    value = read_value(sys.argv[1], sys.argv[2])
    if value:
        sys.stdout.write(value)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
