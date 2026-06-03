"""Anthropic provider: maps the :class:`LLMProvider` contract onto the SDK.

The ``anthropic`` package is imported lazily so the test suite (mock-only, no
network) never needs it installed. Transient SDK errors are normalised to
:class:`TransientLLMError` so the resilience wrapper can retry them; everything
else surfaces as :class:`LLMError`. Always consume this via the resilience
wrapper, never raw.
"""

from __future__ import annotations

import time

from .base import Completion, LLMError, LLMProvider, Message, TransientLLMError


class AnthropicProvider(LLMProvider):
    """Concrete provider backed by the Anthropic Messages API."""

    def __init__(self, *, api_key: str, model: str, request_seconds: float) -> None:
        import anthropic  # lazy: only needed when a real run is wired up

        self._anthropic = anthropic
        self._client = anthropic.Anthropic(api_key=api_key, timeout=request_seconds)
        self._model = model

    def complete(
        self,
        system: str,
        messages: list[Message],
        *,
        temperature: float,
        max_tokens: int,
    ) -> Completion:
        a = self._anthropic
        start = time.perf_counter()
        try:
            resp = self._client.messages.create(
                model=self._model,
                system=system,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except (
            a.APITimeoutError,
            a.APIConnectionError,
            a.RateLimitError,
            a.InternalServerError,
        ) as exc:
            raise TransientLLMError(str(exc)) from exc
        except a.APIError as exc:
            raise LLMError(str(exc)) from exc
        latency_ms = (time.perf_counter() - start) * 1000
        return self._to_completion(resp, latency_ms)

    def _to_completion(self, resp: object, latency_ms: float) -> Completion:
        text = "".join(block.text for block in resp.content if getattr(block, "type", "") == "text")
        return Completion(
            text=text,
            input_tokens=resp.usage.input_tokens,
            output_tokens=resp.usage.output_tokens,
            model=self._model,
            latency_ms=latency_ms,
        )
