"""Tests for the Groq provider (mocked HTTP — no network)."""

from __future__ import annotations

import httpx
import pytest

from debate.llm.base import LLMError, TransientLLMError
from debate.llm.groq import GroqProvider

_MSGS = [{"role": "user", "content": "hi"}]


def _provider() -> GroqProvider:
    return GroqProvider(api_key="gsk_test", model="llama-3.1-8b-instant", request_seconds=5)


def _ok_response() -> httpx.Response:
    return httpx.Response(
        200,
        request=httpx.Request("POST", "https://api.groq.com"),
        json={
            "choices": [{"message": {"content": "hello world"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 3},
        },
    )


def test_successful_completion(monkeypatch) -> None:
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _ok_response())
    result = _provider().complete("sys", _MSGS, temperature=0.5, max_tokens=64)
    assert result.text == "hello world"
    assert result.input_tokens == 10
    assert result.output_tokens == 3
    assert result.model == "llama-3.1-8b-instant"


def test_transient_status_raises_transient(monkeypatch) -> None:
    resp = httpx.Response(429, request=httpx.Request("POST", "https://api.groq.com"))
    monkeypatch.setattr(httpx, "post", lambda *a, **k: resp)
    with pytest.raises(TransientLLMError):
        _provider().complete("sys", _MSGS, temperature=0.5, max_tokens=64)


def test_client_error_raises_llmerror(monkeypatch) -> None:
    resp = httpx.Response(401, request=httpx.Request("POST", "https://api.groq.com"))
    monkeypatch.setattr(httpx, "post", lambda *a, **k: resp)
    with pytest.raises(LLMError):
        _provider().complete("sys", _MSGS, temperature=0.5, max_tokens=64)


def test_network_error_is_transient(monkeypatch) -> None:
    def _boom(*a, **k):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(httpx, "post", _boom)
    with pytest.raises(TransientLLMError):
        _provider().complete("sys", _MSGS, temperature=0.5, max_tokens=64)
