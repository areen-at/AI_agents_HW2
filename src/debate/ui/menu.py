"""Terminal menu — the keyboard-driven front-end over the DebateSDK (Phase 7).

A thin read-eval-print loop: print the menu, read a choice, dispatch to
:class:`~debate.ui.actions.Actions`, print the result, repeat until exit. All
debate behaviour lives in the SDK; this module only handles I/O, so it can be
smoke-tested with scripted stdin (``input_fn``/``output_fn`` are injectable).
"""

from __future__ import annotations

from collections.abc import Callable

from ..sdk import DebateSDK
from .actions import Actions

MENU = """
============================ DEBATE ============================
  [1] Configure   (set topic / rounds for the next run)
  [2] Run         (play a live debate)
  [3] Transcript  (view the last debate's messages)
  [4] Verdict     (view the last decisive verdict)
  [5] Settings    (show active configuration)
  [0] Exit
===============================================================
""".rstrip()


def run(
    sdk: DebateSDK,
    *,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> None:
    """Drive the interactive menu until the user chooses to exit."""
    actions = Actions(sdk)
    while True:
        output_fn(MENU)
        choice = input_fn("Select> ").strip()
        if choice == "0":
            output_fn("Goodbye.")
            return
        try:
            output_fn(_dispatch(actions, choice, input_fn))
        except Exception as exc:  # noqa: BLE001 - menu must survive any action error
            output_fn(f"[error] {exc}")


def _dispatch(actions: Actions, choice: str, input_fn: Callable[[str], str]) -> str:
    """Route a menu choice to the matching action, collecting input as needed."""
    if choice == "1":
        topic = input_fn("Topic (blank = keep current): ")
        rounds = input_fn("Rounds per side (blank = keep current): ")
        return actions.configure(topic, rounds)
    if choice == "2":
        return actions.run()
    if choice == "3":
        return actions.transcript()
    if choice == "4":
        return actions.verdict()
    if choice == "5":
        return actions.settings()
    return f"Unknown option: {choice!r}"
