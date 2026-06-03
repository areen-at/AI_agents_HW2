"""Guard test: no tracked Python file may exceed the 150-line cap.

This keeps the codebase decomposed into small, single-responsibility modules.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from check_file_length import MAX_LINES, find_violations  # noqa: E402


def test_no_python_file_exceeds_cap() -> None:
    violations = find_violations()
    rendered = "\n".join(f"{path}: {lines}" for path, lines in violations)
    assert not violations, f"Files over {MAX_LINES} lines:\n{rendered}"
