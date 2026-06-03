"""A deterministic, no-network mock provider for tests and self-debugging.

``MockLLM`` replays a scripted queue of responses: a ``str`` becomes a
:class:`Completion`, while a queued ``Exception`` is raised (to exercise the
resilience wrapper's retry/breaker paths). A non-zero ``delay`` lets a test
drive the per-request timeout. Canned helpers below produce the "over-agreement"
and "tie / equal-score" payloads later phases assert against.
"""

from __future__ import annotations

import json
import time

from .base import Completion, LLMProvider, Message

_CHARS_PER_TOKEN = 4
_DEFAULT_TEXT = "This is a deterministic mock debate turn."

# Canned outputs reused by later phases (judge intervention / no-tie tests).
OVER_AGREEMENT_TEXT = (
    "I completely agree with you. You are absolutely right and I concede every point you have made."
)


def tie_verdict_json(score: int = 7) -> str:
    """Return a judge payload with deliberately equal scores (a tie attempt)."""
    return json.dumps(
        {
            "winner": "pro",
            "scores": {"pro": score, "con": score},
            "rationale": "Both sides were equally persuasive.",
            "highlights": [],
        }
    )


class MockLLM(LLMProvider):
    """Replays scripted responses with no network, key, or spend."""

    def __init__(
        self,
        responses: list[str | BaseException] | None = None,
        *,
        model: str = "mock-1",
        delay: float = 0.0,
    ) -> None:
        self._queue: list[str | BaseException] = list(responses or [])
        self._model = model
        self._delay = delay
        self.calls: list[dict[str, object]] = []

    def push(self, item: str | BaseException) -> None:
        """Append another scripted response (or exception) to the queue."""
        self._queue.append(item)

    def complete(
        self,
        system: str,
        messages: list[Message],
        *,
        temperature: float,
        max_tokens: int,
    ) -> Completion:
        self.calls.append(
            {
                "system": system,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        )
        if self._delay:
            time.sleep(self._delay)
        item = self._queue.pop(0) if self._queue else _DEFAULT_TEXT
        if isinstance(item, BaseException):
            raise item
        return self._build(system, messages, item)

    def _build(self, system: str, messages: list[Message], text: str) -> Completion:
        chars = len(system) + sum(len(m.get("content", "")) for m in messages)
        return Completion(
            text=text,
            input_tokens=chars // _CHARS_PER_TOKEN,
            output_tokens=max(1, len(text) // _CHARS_PER_TOKEN),
            model=self._model,
            latency_ms=self._delay * 1000,
        )
