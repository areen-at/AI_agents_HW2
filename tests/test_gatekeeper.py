"""Tests for the gatekeeper limits on calls, tokens, and USD."""

from __future__ import annotations

import pytest

from debate.gatekeeper.budget import Usage
from debate.gatekeeper.limiter import BudgetExceededError, Gatekeeper


def _gate(**overrides: float) -> Gatekeeper:
    params = {
        "max_total_calls": 5,
        "max_total_usd": 1.0,
        "max_tokens_total": 10_000,
        "cost_per_mtok_input": 3.0,
        "cost_per_mtok_output": 15.0,
    }
    params.update(overrides)
    return Gatekeeper(**params)  # type: ignore[arg-type]


def test_allows_under_all_limits() -> None:
    gate = _gate()
    gate.check(Usage(calls=1, input_tokens=100, output_tokens=100))
    gate.record(Usage(calls=1, input_tokens=100, output_tokens=100))
    assert not gate.blocked()
    assert gate.budget.calls == 1


def test_blocks_at_call_limit() -> None:
    gate = _gate(max_total_calls=2)
    gate.record(Usage(calls=2))
    with pytest.raises(BudgetExceededError, match="call limit"):
        gate.check(Usage(calls=1))
    assert gate.blocked()


def test_blocks_at_token_limit() -> None:
    gate = _gate(max_tokens_total=1_000)
    with pytest.raises(BudgetExceededError, match="token limit"):
        gate.check(Usage(calls=1, input_tokens=600, output_tokens=600))
    assert gate.blocked()


def test_blocks_at_usd_limit() -> None:
    # 1M output tokens at $15/Mtok = $15 > $1 limit.
    gate = _gate(max_total_usd=1.0, max_tokens_total=10_000_000)
    with pytest.raises(BudgetExceededError, match="USD limit"):
        gate.check(Usage(calls=1, output_tokens=1_000_000))
    assert gate.blocked()


def test_record_latches_blocked_on_overshoot() -> None:
    gate = _gate(max_total_calls=1)
    gate.record(Usage(calls=2))  # actual usage overshoots the limit
    assert gate.blocked()


def test_cost_estimate_uses_rates() -> None:
    gate = _gate()
    cost = gate.budget.cost_usd(Usage(input_tokens=1_000_000, output_tokens=1_000_000))
    assert cost == pytest.approx(18.0)
