"""Tests that planted secrets are masked by the redactor."""

from __future__ import annotations

from debate.observability.redaction import MASK, redact


def test_masks_provider_key() -> None:
    out = redact("using key sk-ant-ABCDEF123456 now")
    assert "ABCDEF123456" not in out
    assert MASK in out


def test_masks_bearer_token() -> None:
    out = redact("Authorization: Bearer abcdef123456TOKEN")
    assert "abcdef123456TOKEN" not in out
    assert "Bearer" in out


def test_masks_key_value_assignment() -> None:
    out = redact('api_key="superSecretValue123"')
    assert "superSecretValue123" not in out
    assert "api_key" in out.lower()


def test_benign_text_untouched() -> None:
    text = "Barcelona scored three goals in the second half."
    assert redact(text) == text


def test_empty_string() -> None:
    assert redact("") == ""
