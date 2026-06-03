"""Tests for the deterministic MockLLM provider."""

from __future__ import annotations

import json

import pytest

from debate.llm.mock import OVER_AGREEMENT_TEXT, MockLLM, tie_verdict_json

_MSGS = [{"role": "user", "content": "topic"}]


def _complete(mock: MockLLM):
    return mock.complete("system", _MSGS, temperature=0.7, max_tokens=100)


def test_scripted_text_returns_completion() -> None:
    mock = MockLLM(["first", "second"])
    assert _complete(mock).text == "first"
    assert _complete(mock).text == "second"


def test_default_text_when_queue_empty() -> None:
    mock = MockLLM()
    result = _complete(mock)
    assert result.text
    assert result.tokens_used == result.input_tokens + result.output_tokens


def test_queued_exception_is_raised() -> None:
    mock = MockLLM([ValueError("boom")])
    with pytest.raises(ValueError, match="boom"):
        _complete(mock)


def test_calls_are_recorded() -> None:
    mock = MockLLM(["x"])
    _complete(mock)
    assert mock.calls[0]["temperature"] == 0.7
    assert mock.calls[0]["max_tokens"] == 100


def test_canned_outputs() -> None:
    assert "agree" in OVER_AGREEMENT_TEXT.lower()
    scores = json.loads(tie_verdict_json(5))["scores"]
    assert scores["pro"] == scores["con"] == 5
