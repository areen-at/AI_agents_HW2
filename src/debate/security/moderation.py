"""Content moderation: respectful-tone policy + per-turn word cap (PRD §4.2 / NFR-7).

Debaters may lie and argue forcefully, but they may not curse or sling insults,
and no turn may exceed the configured word cap. :meth:`Moderator.check_text`
returns ``(ok, reason)`` so the caller can reject or trim an offending turn.
"""

from __future__ import annotations

import re

# Default disallowed terms: profanity + personal insults that breach the
# respectful-tone policy. Overridable via config (a custom banned-terms list).
DEFAULT_BANNED_TERMS: tuple[str, ...] = (
    "damn",
    "hell",
    "crap",
    "idiot",
    "stupid",
    "moron",
    "dumb",
    "shut up",
    "bastard",
    "ass",
)


def _count_words(text: str) -> int:
    return len(text.split())


class Moderator:
    """Flags offensive language and over-long turns against config-driven limits."""

    def __init__(
        self,
        *,
        max_words: int,
        banned_terms: tuple[str, ...] | list[str] | None = None,
    ) -> None:
        self._max_words = max_words
        terms = banned_terms if banned_terms is not None else DEFAULT_BANNED_TERMS
        self._terms = tuple(t.lower() for t in terms)
        # Word-boundary, case-insensitive match to avoid the Scunthorpe problem.
        self._pattern = re.compile(
            r"\b(?:" + "|".join(re.escape(t) for t in self._terms) + r")\b",
            flags=re.IGNORECASE,
        )

    def check_text(self, text: str) -> tuple[bool, str | None]:
        """Return ``(True, None)`` if ``text`` is acceptable, else ``(False, reason)``.

        Word cap is checked first (cheapest, most common rejection), then tone.
        """
        words = _count_words(text)
        if words > self._max_words:
            return False, f"exceeds word cap: {words} > {self._max_words}"

        match = self._pattern.search(text)
        if match:
            return False, f"offensive/disrespectful term: {match.group(0)!r}"

        return True, None
