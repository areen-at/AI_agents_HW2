"""Entry point: ``python -m debate`` launches the terminal menu (Phase 7).

Loads and validates the config into a :class:`~debate.sdk.DebateSDK`, then hands
control to the keyboard menu. Provider API keys are *not* required to open the
menu — they are resolved lazily only when a debate is actually run, so the
interface stays usable for inspection without secrets configured.
"""

from __future__ import annotations

from pydantic import ValidationError

from .sdk import DebateSDK
from .ui.menu import run as run_menu

BANNER = r"""
==============================================================
   DEBATE  --  Pro  vs  Con   (judged by a topic-blind Father)
   Child -> Father -> Child   |   persuasion, not truth
==============================================================
"""


def main() -> int:
    """Print the banner, build the SDK from config, and run the menu."""
    print(BANNER)
    try:
        sdk = DebateSDK.from_path()
    except (FileNotFoundError, ValidationError, ValueError) as exc:
        print(f"[startup error] {exc}")
        return 1
    run_menu(sdk)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
