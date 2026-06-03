"""The Gatekeeper: hard limits on calls, tokens, and USD spend (PRD §4.2 / NFR-5).

``check`` is called *before* an LLM/tool request with an estimate; it raises
:class:`BudgetExceededError` if proceeding would cross any configured limit. ``record``
folds the actual usage in afterwards. Once any limit is hit the gate latches
``blocked`` so the engine can halt the whole run.
"""

from __future__ import annotations

from .budget import Budget, Usage


class BudgetExceededError(RuntimeError):
    """Raised by :meth:`Gatekeeper.check` when a limit would be crossed."""


class Gatekeeper:
    """Enforces spend/usage ceilings; blocks the run before they are exceeded."""

    def __init__(
        self,
        *,
        max_total_calls: int,
        max_total_usd: float,
        max_tokens_total: int,
        cost_per_mtok_input: float,
        cost_per_mtok_output: float,
    ) -> None:
        self._max_calls = max_total_calls
        self._max_usd = max_total_usd
        self._max_tokens = max_tokens_total
        self._budget = Budget(
            cost_per_mtok_input=cost_per_mtok_input,
            cost_per_mtok_output=cost_per_mtok_output,
        )
        self._blocked = False

    @property
    def budget(self) -> Budget:
        return self._budget

    def blocked(self) -> bool:
        """Whether a limit has already been hit (run should halt)."""
        return self._blocked

    def check(self, estimated: Usage) -> None:
        """Veto a pending call whose ``estimated`` usage would breach a limit.

        Raises :class:`BudgetExceededError` and latches :meth:`blocked` on violation.
        """
        calls = self._budget.calls + estimated.calls
        tokens = self._budget.total_tokens + estimated.total_tokens
        usd = self._budget.total_usd + self._budget.cost_usd(estimated)

        reason = self._first_violation(calls, tokens, usd)
        if reason is not None:
            self._blocked = True
            raise BudgetExceededError(reason)

    def record(self, actual: Usage) -> None:
        """Fold the actual usage of a completed call into the totals."""
        self._budget.add(actual)
        if self._first_violation(
            self._budget.calls, self._budget.total_tokens, self._budget.total_usd
        ):
            self._blocked = True

    def _first_violation(self, calls: int, tokens: int, usd: float) -> str | None:
        """Return a message for the first breached limit, else ``None``."""
        if calls > self._max_calls:
            return f"call limit reached: {calls} > {self._max_calls}"
        if tokens > self._max_tokens:
            return f"token limit reached: {tokens} > {self._max_tokens}"
        if usd > self._max_usd:
            return f"USD limit reached: {usd:.4f} > {self._max_usd:.4f}"
        return None
