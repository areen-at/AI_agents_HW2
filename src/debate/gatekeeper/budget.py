"""Usage accounting: running totals of calls, tokens, and USD spend.

Pure bookkeeping — no policy decisions live here. Cost is estimated from the
per-million-token rates supplied in config, so the limiter can veto a call
*before* it is made as well as record the actual cost afterwards.
"""

from __future__ import annotations

from dataclasses import dataclass

_PER_MILLION = 1_000_000


@dataclass(frozen=True)
class Usage:
    """A single unit of usage (estimated before a call, actual after)."""

    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


class Budget:
    """Accumulates usage and converts token counts into a USD estimate."""

    def __init__(self, *, cost_per_mtok_input: float, cost_per_mtok_output: float) -> None:
        self._in_rate = cost_per_mtok_input
        self._out_rate = cost_per_mtok_output
        self.calls = 0
        self.input_tokens = 0
        self.output_tokens = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    def cost_usd(self, usage: Usage) -> float:
        """Estimate the USD cost of ``usage`` from the configured rates."""
        return (
            usage.input_tokens * self._in_rate + usage.output_tokens * self._out_rate
        ) / _PER_MILLION

    @property
    def total_usd(self) -> float:
        """USD spent so far across all recorded usage."""
        return self.cost_usd(Usage(0, self.input_tokens, self.output_tokens))

    def add(self, usage: Usage) -> None:
        """Fold ``usage`` into the running totals."""
        self.calls += usage.calls
        self.input_tokens += usage.input_tokens
        self.output_tokens += usage.output_tokens
