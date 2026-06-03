"""Optional OpenAI provider: maps the contract onto the Chat Completions API.

The ``openai`` package is imported lazily (it is an optional extra) so the
mock-only test suite never requires it. Transient SDK errors become
:class:`TransientLLMError` for the resilience wrapper to retry. Always consume
this via the resilience wrapper, never raw.
"""

from __future__ import annotations

import time

from .base import Completion, LLMError, LLMProvider, Message, TransientLLMError


class OpenAIProvider(LLMProvider):
    """Concrete provider backed by the OpenAI Chat Completions API."""

    def __init__(self, *, api_key: str, model: str, request_seconds: float) -> None:
        import openai  # lazy: optional extra, only needed for a real run

        self._openai = openai
        self._client = openai.OpenAI(api_key=api_key, timeout=request_seconds)
        self._model = model

    def complete(
        self,
        system: str,
        messages: list[Message],
        *,
        temperature: float,
        max_tokens: int,
    ) -> Completion:
        o = self._openai
        chat = [{"role": "system", "content": system}, *messages]
        start = time.perf_counter()
        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=chat,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except (o.APITimeoutError, o.APIConnectionError, o.RateLimitError) as exc:
            raise TransientLLMError(str(exc)) from exc
        except o.APIError as exc:
            raise LLMError(str(exc)) from exc
        latency_ms = (time.perf_counter() - start) * 1000
        return self._to_completion(resp, latency_ms)

    def _to_completion(self, resp: object, latency_ms: float) -> Completion:
        return Completion(
            text=resp.choices[0].message.content or "",
            input_tokens=resp.usage.prompt_tokens,
            output_tokens=resp.usage.completion_tokens,
            model=self._model,
            latency_ms=latency_ms,
        )
