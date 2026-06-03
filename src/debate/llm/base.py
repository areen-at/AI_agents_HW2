"""LLM provider contract: a vendor-neutral text-completion interface.

Every agent talks to an :class:`LLMProvider`; concrete providers (Anthropic,
OpenAI, mock) map this contract onto a vendor SDK. They are always wrapped by
:class:`~debate.llm.resilience.ResilientProvider` — the single choke-point that
adds timeout, retry/backoff, circuit-breaking, and gatekeeper accounting, so no
agent ever calls a vendor SDK directly.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

# One chat turn: {"role": "user"|"assistant", "content": "..."}.
Message = dict[str, str]


class LLMError(RuntimeError):
    """Base class for all provider-layer failures."""


class TransientLLMError(LLMError):
    """A retryable failure (network blip, rate limit, 5xx)."""


class LLMTimeoutError(LLMError):
    """A request exceeded its per-call time budget."""


class CircuitOpenError(LLMError):
    """The breaker is open; the call was rejected without an attempt."""


@dataclass(frozen=True)
class Completion:
    """A single model response plus the metadata logs/gatekeeper need."""

    text: str
    input_tokens: int
    output_tokens: int
    model: str
    latency_ms: float

    @property
    def tokens_used(self) -> int:
        return self.input_tokens + self.output_tokens


class LLMProvider(ABC):
    """Vendor-neutral text-completion interface."""

    @abstractmethod
    def complete(
        self,
        system: str,
        messages: list[Message],
        *,
        temperature: float,
        max_tokens: int,
    ) -> Completion:
        """Return a :class:`Completion` for ``system`` + ``messages``."""
        raise NotImplementedError
