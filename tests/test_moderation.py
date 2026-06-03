"""Tests for content moderation: tone policy + per-turn word cap."""

from __future__ import annotations

from debate.security.moderation import Moderator


def test_clean_respectful_text_passes() -> None:
    mod = Moderator(max_words=150)
    ok, reason = mod.check_text("Real Madrid's Champions League record is unmatched.")
    assert ok is True
    assert reason is None


def test_cursing_is_flagged() -> None:
    mod = Moderator(max_words=150)
    ok, reason = mod.check_text("That argument is just plain stupid, you idiot.")
    assert ok is False
    assert reason is not None and "term" in reason


def test_over_word_limit_is_flagged() -> None:
    mod = Moderator(max_words=10)
    ok, reason = mod.check_text("word " * 20)
    assert ok is False
    assert reason is not None and "word cap" in reason


def test_custom_banned_terms_override_default() -> None:
    mod = Moderator(max_words=150, banned_terms=["frobnicate"])
    # A default banned word is now allowed; the custom one is caught.
    assert mod.check_text("That is stupid.")[0] is True
    assert mod.check_text("Do not frobnicate the data.")[0] is False


def test_substring_does_not_false_positive() -> None:
    # "class" contains "ass" but must not trip the word-boundary matcher.
    mod = Moderator(max_words=150)
    ok, _ = mod.check_text("The class showed great passing in midfield.")
    assert ok is True
