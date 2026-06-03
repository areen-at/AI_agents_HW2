"""Router — enforces the Child → Father → Child relay (Phase 6.1).

Debaters only ever address the judge; there is **no direct Pro↔Con path** in the
API. The router takes a debater's message (always sent *to* the judge), asks the
judge to relay it to the opponent, and — when the debater is conceding/agreeing —
adds an anti-agreement intervention aimed back at that same debater. The relay
itself carries no model call; intervention does (via the judge).
"""

from __future__ import annotations

from dataclasses import dataclass

from ..agents.judge import JudgeAgent
from ..protocol.message import Message, Party


class RoutingError(RuntimeError):
    """Raised when a message violates the child → father → child rule."""


@dataclass(frozen=True)
class RouteResult:
    """The judge's relay to the opponent, plus an optional intervention."""

    relay: Message
    intervention: Message | None = None


class Router:
    """Funnels every debater turn through the judge; blocks direct debater traffic."""

    def __init__(self, judge: JudgeAgent, *, logger: object | None = None) -> None:
        self._judge = judge
        self._logger = logger

    def route(self, message: Message, round: int) -> RouteResult:
        """Relay a debater message via the judge, intervening on over-agreement."""
        if message.sender is Party.JUDGE or message.recipient is not Party.JUDGE:
            raise RoutingError(
                "debater messages must be addressed to the judge "
                f"(got {message.sender.value} -> {message.recipient.value})"
            )
        relay = self._judge.relay(message, round)
        intervention: Message | None = None
        if self._judge.should_intervene(message.payload.text):
            self._log("router_intervention", debater=message.sender.value, round=round)
            intervention = self._judge.intervene(message.sender, "over-agreement detected", round)
        return RouteResult(relay=relay, intervention=intervention)

    def _log(self, event: str, **fields: object) -> None:
        log = getattr(self._logger, "log", None)
        if callable(log):
            log(event, **fields)
