"""The single resilience choke-point wrapping every concrete provider.

``ResilientProvider`` adds, in order: a gatekeeper budget *check*, a circuit
breaker, a hard per-request timeout, and bounded retry-with-backoff on transient
failures. On success it *records* actual usage with the gatekeeper and emits a
redacted log line. No agent ever calls a vendor SDK directly — they go through
this wrapper, so all resilience and accounting live in one place.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout

from ..gatekeeper.budget import Usage
from ..gatekeeper.limiter import Gatekeeper
from .base import (
    CircuitOpenError,
    Completion,
    LLMError,
    LLMProvider,
    LLMTimeoutError,
    Message,
    TransientLLMError,
)
from .circuit import CircuitBreaker

_CHARS_PER_TOKEN = 4


class ResilientProvider(LLMProvider):
    """Wraps an ``inner`` provider with timeout, retry, breaker, and accounting."""

    def __init__(
        self,
        inner: LLMProvider,
        *,
        request_seconds: float,
        retries: int,
        backoff_seconds: float,
        breaker_threshold: int,
        gatekeeper: Gatekeeper | None = None,
        logger: object | None = None,
    ) -> None:
        self._inner = inner
        self._request_seconds = request_seconds
        self._retries = retries
        self._backoff_seconds = backoff_seconds
        self._breaker = CircuitBreaker(breaker_threshold)
        self._gatekeeper = gatekeeper
        self._logger = logger

    def complete(
        self,
        system: str,
        messages: list[Message],
        *,
        temperature: float,
        max_tokens: int,
    ) -> Completion:
        if self._gatekeeper is not None:
            self._gatekeeper.check(self._estimate(system, messages, max_tokens))
        if self._breaker.is_open:
            self._log("llm_circuit_open")
            raise CircuitOpenError("circuit breaker is open")
        return self._attempt_loop(system, messages, temperature, max_tokens)

    def _attempt_loop(
        self,
        system: str,
        messages: list[Message],
        temperature: float,
        max_tokens: int,
    ) -> Completion:
        last: LLMError | None = None
        for attempt in range(self._retries + 1):
            try:
                completion = self._call_with_timeout(system, messages, temperature, max_tokens)
            except (TransientLLMError, LLMTimeoutError) as exc:
                last = exc
                self._breaker.record_failure()
                self._log("llm_attempt_failed", attempt=attempt, error=str(exc))
                if self._breaker.is_open or attempt == self._retries:
                    break
                if self._backoff_seconds:
                    time.sleep(self._backoff_seconds * (attempt + 1))
                continue
            self._on_success(completion)
            return completion
        raise last if last is not None else LLMError("completion failed")

    def _on_success(self, completion: Completion) -> None:
        self._breaker.record_success()
        if self._gatekeeper is not None:
            self._gatekeeper.record(
                Usage(
                    calls=1,
                    input_tokens=completion.input_tokens,
                    output_tokens=completion.output_tokens,
                )
            )
        self._log(
            "llm_call_ok",
            model=completion.model,
            latency_ms=completion.latency_ms,
            tokens=completion.tokens_used,
        )

    def _call_with_timeout(
        self,
        system: str,
        messages: list[Message],
        temperature: float,
        max_tokens: int,
    ) -> Completion:
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(
            self._inner.complete,
            system,
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        try:
            return future.result(timeout=self._request_seconds)
        except FuturesTimeout as exc:
            raise LLMTimeoutError(f"request exceeded {self._request_seconds}s") from exc
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    def _estimate(self, system: str, messages: list[Message], max_tokens: int) -> Usage:
        chars = len(system) + sum(len(m.get("content", "")) for m in messages)
        return Usage(
            calls=1,
            input_tokens=chars // _CHARS_PER_TOKEN,
            output_tokens=max_tokens,
        )

    def _log(self, event: str, **fields: object) -> None:
        log = getattr(self._logger, "log", None)
        if callable(log):
            log(event, **fields)
