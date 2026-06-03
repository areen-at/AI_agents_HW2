"""Entry point: ``python -m debate`` launches the terminal menu.

The menu is added in Phase 7. For now this prints a banner so the
skeleton is runnable and the packaging is verifiable end-to-end.
"""

from __future__ import annotations

BANNER = r"""
==============================================================
   DEBATE  --  Pro  vs  Con   (judged by a topic-blind Father)
   Child -> Father -> Child   |   persuasion, not truth
==============================================================
  Skeleton ready. Terminal menu arrives in Phase 7.
"""


def main() -> int:
    """Print the banner. Returns a process exit code."""
    print(BANNER)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
