"""Secret resolution from the environment, with leak-safe error messages.

Secrets are never written to ``config.yaml``; they live only in ``.env`` /
the process environment. Error messages name the *missing variable* but never
echo a value, and :func:`mask_secret` renders a safe preview for logs/UI.
"""

from __future__ import annotations

import os


class MissingSecretError(RuntimeError):
    """Raised when a required secret is absent from the environment."""


def get_secret(name: str, *, required: bool = True) -> str | None:
    """Return the env var ``name``.

    Raises :class:`MissingSecretError` when ``required`` and the variable is
    unset or blank. The message contains only the variable *name* — never an
    expected or actual value — so it is safe to log.
    """
    value = os.environ.get(name)
    if value:
        return value
    if required:
        raise MissingSecretError(
            f"Required secret {name!r} is not set. Copy .env.example to .env and fill it in."
        )
    return None


def mask_secret(value: str, *, visible: int = 4) -> str:
    """Render a secret as ``sk-...abcd`` for safe display.

    Shows an optional non-secret prefix (up to the first ``-``) and the last
    ``visible`` characters; everything else becomes an ellipsis. Short or empty
    values collapse to ``***`` so nothing meaningful leaks.
    """
    if not value or len(value) <= visible:
        return "***"
    prefix = ""
    head, sep, _ = value.partition("-")
    if sep and len(head) <= 6:
        prefix = f"{head}-"
    return f"{prefix}...{value[-visible:]}"
