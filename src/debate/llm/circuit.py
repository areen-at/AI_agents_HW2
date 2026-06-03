"""A minimal consecutive-failure circuit breaker.

The breaker opens after ``threshold`` consecutive failures and stays open until
a success resets it. While open, :class:`~debate.llm.resilience.ResilientProvider`
rejects calls immediately instead of hammering a failing backend.
"""

from __future__ import annotations


class CircuitBreaker:
    """Trips open after ``threshold`` consecutive failures."""

    def __init__(self, threshold: int) -> None:
        if threshold < 1:
            raise ValueError("circuit breaker threshold must be >= 1")
        self._threshold = threshold
        self._failures = 0
        self._open = False

    @property
    def is_open(self) -> bool:
        """Whether the breaker is currently rejecting calls."""
        return self._open

    def record_success(self) -> None:
        """Reset the failure streak and close the breaker."""
        self._failures = 0
        self._open = False

    def record_failure(self) -> None:
        """Count a failure and open the breaker once the streak hits the cap."""
        self._failures += 1
        if self._failures >= self._threshold:
            self._open = True
