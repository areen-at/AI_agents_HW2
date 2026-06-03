"""Tests for the resilience wrapper: timeout, retry, breaker, gatekeeper."""

from __future__ import annotations

import pytest

from debate.gatekeeper.budget import Usage
from debate.gatekeeper.limiter import Gatekeeper
from debate.llm.base import (
    CircuitOpenError,
    Completion,
    LLMTimeoutError,
    TransientLLMError,
)
from debate.llm.mock import MockLLM
from debate.llm.resilience import ResilientProvider


class _SpyGate(Gatekeeper):
    """Gatekeeper that counts check/record invocations."""

    def __init__(self, **kw: float) -> None:
        super().__init__(**kw)
        self.checks = 0
        self.records = 0

    def check(self, estimated: Usage) -> None:
        self.checks += 1
        super().check(estimated)

    def record(self, actual: Usage) -> None:
        self.records += 1
        super().record(actual)


def _gate() -> _SpyGate:
    return _SpyGate(
        max_total_calls=100,
        max_total_usd=10.0,
        max_tokens_total=1_000_000,
        cost_per_mtok_input=3.0,
        cost_per_mtok_output=15.0,
    )


def _wrap(inner: MockLLM, **overrides: object) -> ResilientProvider:
    params: dict[str, object] = {
        "request_seconds": 5.0,
        "retries": 2,
        "backoff_seconds": 0.0,
        "breaker_threshold": 3,
    }
    params.update(overrides)
    return ResilientProvider(inner, **params)  # type: ignore[arg-type]


def _complete(provider: ResilientProvider) -> Completion:
    return provider.complete(
        "sys", [{"role": "user", "content": "hi"}], temperature=0.5, max_tokens=64
    )


def test_timeout_path_handled() -> None:
    provider = _wrap(MockLLM(delay=0.2), request_seconds=0.05)
    with pytest.raises(LLMTimeoutError):
        _complete(provider)


def test_retry_on_transient_then_success() -> None:
    inner = MockLLM([TransientLLMError("blip"), "recovered"])
    provider = _wrap(inner, retries=2)
    result = _complete(provider)
    assert result.text == "recovered"
    assert len(inner.calls) == 2


def test_circuit_breaker_trips_after_threshold() -> None:
    inner = MockLLM([TransientLLMError("x")] * 5)
    provider = _wrap(inner, retries=0, breaker_threshold=3)
    for _ in range(3):
        with pytest.raises(TransientLLMError):
            _complete(provider)
    with pytest.raises(CircuitOpenError):
        _complete(provider)


def test_gatekeeper_invoked_check_and_record() -> None:
    gate = _gate()
    provider = _wrap(MockLLM(["ok"]), gatekeeper=gate)
    _complete(provider)
    assert gate.checks == 1
    assert gate.records == 1
    assert gate.budget.calls == 1
