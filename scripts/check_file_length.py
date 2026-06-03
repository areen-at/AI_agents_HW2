#!/usr/bin/env python3
"""Enforce the project-wide 150-line cap on Python source files.

Used as a pre-commit hook, a CI step, and by ``tests/test_file_length.py``.
Run directly to scan the whole repo::

    python scripts/check_file_length.py

Exits non-zero (and prints offenders) if any tracked ``.py`` exceeds the cap.
"""

from __future__ import annotations

import sys
from pathlib import Path

MAX_LINES = 150
SCAN_DIRS = ("src", "tests", "scripts")
REPO_ROOT = Path(__file__).resolve().parent.parent


def count_lines(path: Path) -> int:
    """Return the number of lines in ``path`` (newline-terminated tolerant)."""
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for _ in handle)


def find_violations(root: Path = REPO_ROOT, limit: int = MAX_LINES) -> list[tuple[Path, int]]:
    """Return ``(path, line_count)`` for every ``.py`` file over ``limit``."""
    violations: list[tuple[Path, int]] = []
    for directory in SCAN_DIRS:
        base = root / directory
        if not base.exists():
            continue
        for path in sorted(base.rglob("*.py")):
            lines = count_lines(path)
            if lines > limit:
                violations.append((path.relative_to(root), lines))
    return violations


def main() -> int:
    """Print any violations and return a process exit code."""
    violations = find_violations()
    if not violations:
        print(f"OK: all .py files are within {MAX_LINES} lines.")
        return 0
    print(f"FAIL: {len(violations)} file(s) exceed the {MAX_LINES}-line cap:")
    for path, lines in violations:
        print(f"  {path}: {lines} lines (+{lines - MAX_LINES})")
    return 1


if __name__ == "__main__":
    sys.exit(main())
