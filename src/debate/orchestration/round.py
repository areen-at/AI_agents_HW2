"""Round — one Pro→Con exchange routed through the judge (Phase 6.2).

A single round is one Pro turn followed by one Con turn. Each turn is produced
by the debater (addressed to the judge), relayed by the judge to the opponent,
and the relay is fed to that opponent next — guaranteeing **mutual response**
with the opponent's prior message linked via ``rebuts_message_id``. Pro's very
first turn opens with the motion; every later turn rebuts the last relay it
received. Each turn runs through ``guard`` (the watchdog) so a hang is contained.
"""

from __future__ import annotations

from collections.abc import Callable

from ..agents.debater import DebaterAgent
from ..protocol.message import Message, Party
from .router import Router
from .transcript import Transcript


class Round:
    """Plays consecutive rounds, carrying each side's last relayed message."""

    def __init__(
        self,
        *,
        pro: DebaterAgent,
        con: DebaterAgent,
        router: Router,
        transcript: Transcript,
        guard: Callable[[str, Callable[[], Message]], Message] | None = None,
        topic: str = "",
    ) -> None:
        self._pro = pro
        self._con = con
        self._router = router
        self._transcript = transcript
        self._guard = guard or (lambda _label, fn: fn())
        self._topic = topic
        self._to_pro: Message | None = None
        self._to_con: Message | None = None

    def play(self, number: int) -> None:
        """Run one full exchange: Pro speaks, is relayed; then Con; then relayed."""
        self._turn(self._pro, incoming=self._to_pro, number=number)
        self._turn(self._con, incoming=self._to_con, number=number)

    def _turn(self, agent: DebaterAgent, *, incoming: Message | None, number: int) -> None:
        label = f"{agent.role.value}_turn_r{number}"
        message = self._guard(label, lambda: self._act(agent, incoming, number))
        self._transcript.add(message)
        result = self._router.route(message, number)
        self._transcript.add(result.relay)
        if result.intervention is not None:
            self._transcript.add(result.intervention)
        self._deliver(agent.role, result.relay)

    def _act(self, agent: DebaterAgent, incoming: Message | None, number: int) -> Message:
        if incoming is None:
            context = f"The motion under debate is: {self._topic}" if self._topic else ""
            return agent.argue(number, context=context)
        return agent.rebut(incoming, number)

    def _deliver(self, role: Party, relay: Message) -> None:
        if role is Party.PRO:
            self._to_con = relay
        else:
            self._to_pro = relay
