"""Structured JSON-line logger with FIFO rotation (PRD §4.3 / NFR-6).

Each entry is one JSON line. A file holds at most ``max_lines_per_file`` lines;
when full, a new file rolls. At most ``max_files`` files are kept — the oldest
is deleted first. Every line passes through :func:`redact` before it is written.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .redaction import redact

_FILE_PREFIX = "debate-"
_FILE_GLOB = f"{_FILE_PREFIX}*.jsonl"


class FifoLogger:
    """Append-only JSON-line logger that rotates and prunes files in FIFO order."""

    def __init__(
        self,
        directory: str | Path,
        *,
        max_files: int,
        max_lines_per_file: int,
        level: str = "INFO",
    ) -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.max_files = max_files
        self.max_lines_per_file = max_lines_per_file
        self.level = level
        self._current: Path | None = None
        self._lines = 0
        self._seq = self._next_seq()

    def log(self, event: str, **fields: Any) -> None:
        """Write one redacted JSON entry; rotate/prune as needed."""
        record = {
            "ts": datetime.now(UTC).isoformat(),
            "level": self.level,
            "event": event,
            **fields,
        }
        line = redact(json.dumps(record, ensure_ascii=False, default=str))
        with self._target().open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
        self._lines += 1

    def _target(self) -> Path:
        """Return the file to append to, rolling a new one when full."""
        if self._current is None or self._lines >= self.max_lines_per_file:
            self._roll()
        if self._current is None:  # pragma: no cover - _roll always sets it
            raise RuntimeError("log file was not initialised")
        return self._current

    def _next_seq(self) -> int:
        """Resume the sequence after the highest existing file index."""
        highest = 0
        for path in self.directory.glob(_FILE_GLOB):
            try:
                highest = max(highest, int(path.stem.split("-")[-1]))
            except ValueError:  # pragma: no cover - foreign filename
                continue
        return highest + 1

    def _roll(self) -> None:
        """Open a fresh, uniquely-named log file and enforce the file cap."""
        name = f"{_FILE_PREFIX}{self._seq:012d}.jsonl"
        self._seq += 1
        self._current = self.directory / name
        self._current.touch()
        self._lines = 0
        self._prune()

    def _prune(self) -> None:
        """Delete oldest files until at most ``max_files`` remain (FIFO)."""
        files = sorted(self.directory.glob(_FILE_GLOB))
        excess = len(files) - self.max_files
        for path in files[:excess] if excess > 0 else []:
            path.unlink(missing_ok=True)
