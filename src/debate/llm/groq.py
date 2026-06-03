"""Groq provider via the OpenAI-compatible Chat Completions endpoint.

Groq speaks the OpenAI Chat Completions schema, so this provider calls it
directly over ``httpx`` (already a dependency) — no extra SDK. Retryable HTTP
statuses and network errors normalise to :class:`TransientLLMError` so the
resilience wrapper can retry. Always consume via that wrapper, never raw.
"""

from __future__ import annotations

import time

import httpx

from .base import Completion, LLMError, LLMProvider, Message, TransientLLMError

_URL = "https://api.groq.com/openai/v1/chat/completions"
_TRANSIENT_STATUS = frozenset({408, 409, 425, 429, 500, 502, 503, 504})


class GroqProvider(LLMProvider):
    """Concrete provider backed by Groq's OpenAI-compatible API."""

    def __init__(self, *, api_key: str, model: str, request_seconds: float) -> None:
        self._model = model
        self._timeout = request_seconds
        self._headers = {"Authorization": f"Bearer {api_key}"}

    def complete(
        self,
        system: str,
        messages: list[Message],
        *,
        temperature: float,
        max_tokens: int,
    ) -> Completion:
        payload = {
            "model": self._model,
            "messages": [{"role": "system", "content": system}, *messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        start = time.perf_counter()
        try:
            resp = httpx.post(_URL, headers=self._headers, json=payload, timeout=self._timeout)
        except httpx.HTTPError as exc:
            raise TransientLLMError(f"groq request failed: {exc}") from exc
        self._raise_for_status(resp)
        latency_ms = (time.perf_counter() - start) * 1000
        return self._to_completion(resp.json(), latency_ms)

    @staticmethod
    def _raise_for_status(resp: httpx.Response) -> None:
        if resp.status_code in _TRANSIENT_STATUS:
            raise TransientLLMError(f"groq transient status {resp.status_code}")
        if resp.status_code >= 400:
            raise LLMError(f"groq error status {resp.status_code}")

    def _to_completion(self, data: dict, latency_ms: float) -> Completion:
        usage = data.get("usage", {})
        return Completion(
            text=data["choices"][0]["message"]["content"] or "",
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            model=self._model,
            latency_ms=latency_ms,
        )
