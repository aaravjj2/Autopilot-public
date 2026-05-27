"""Zero-copy Kalshi tick file reader via mmap (Week 1 Day 5)."""

from __future__ import annotations

import json
import mmap
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional


@dataclass
class KalshiTick:
    """Parsed tick from append-only JSONL mmap file."""

    offset: int
    ticker: str
    payload: dict


class KalshiTickMmapReader:
    """
    Reads newline-delimited JSON ticks from a file using mmap.
    Writer appends one JSON object per line for zero-copy tail reads.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._file = None
        self._mmap: Optional[mmap.mmap] = None

    def open(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.touch()
        self._file = open(self.path, "r+b")
        size = os.path.getsize(self.path)
        if size == 0:
            self._mmap = None
            return
        self._mmap = mmap.mmap(self._file.fileno(), 0, access=mmap.ACCESS_READ)

    def close(self) -> None:
        if self._mmap is not None:
            self._mmap.close()
            self._mmap = None
        if self._file is not None:
            self._file.close()
            self._file = None

    def __enter__(self) -> KalshiTickMmapReader:
        self.open()
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def iter_ticks(self, *, from_offset: int = 0) -> Iterator[KalshiTick]:
        if self._mmap is None:
            return
        data = self._mmap
        start = from_offset
        while True:
            nl = data.find(b"\n", start)
            if nl == -1:
                break
            line = data[start:nl]
            start = nl + 1
            if not line.strip():
                continue
            try:
                payload = json.loads(line.decode("utf-8"))
            except json.JSONDecodeError:
                continue
            ticker = str(payload.get("ticker") or payload.get("market_ticker") or "")
            yield KalshiTick(offset=start, ticker=ticker, payload=payload)

    @staticmethod
    def append_tick(path: str | Path, payload: dict) -> int:
        """Append one tick line; returns file offset before write."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        offset = p.stat().st_size if p.exists() else 0
        with open(p, "ab") as f:
            f.write((json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8"))
        return offset
