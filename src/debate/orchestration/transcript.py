"""Transcript — ordered message store, JSON persistence, human-readable export.

Every message produced during a debate is appended here in order and persisted
as a redacted JSON line through the FIFO logger. The full record can be dumped
as a JSON array, rendered for humans, or reduced to just the debaters' turns
(``debate_text``) — the topic-blind view the judge scores at the end.
"""

from __future__ import annotations

import json

from ..protocol.message import Message, MessageType, Party

_LABELS = {Party.PRO: "PRO", Party.CON: "CON", Party.JUDGE: "JUDGE"}
_DEBATE_TYPES = (MessageType.ARGUMENT, MessageType.REBUTTAL)


class Transcript:
    """Accumulates the debate's messages and exports them in several forms."""

    def __init__(self, *, logger: object | None = None) -> None:
        self._messages: list[Message] = []
        self._logger = logger

    def add(self, message: Message) -> None:
        """Append a message and persist a redacted JSON-line record of it."""
        self._messages.append(message)
        self._log(
            "transcript_message",
            message_id=message.message_id,
            type=message.type.value,
            sender=message.sender.value,
            recipient=message.recipient.value,
            round=message.round,
            rebuts=message.payload.rebuts_message_id,
        )

    @property
    def messages(self) -> tuple[Message, ...]:
        """The full ordered sequence of messages."""
        return tuple(self._messages)

    def count_turns(self, sender: Party) -> int:
        """Number of argument/rebuttal turns produced by ``sender``."""
        return sum(1 for m in self._messages if m.sender is sender and m.type in _DEBATE_TYPES)

    def as_json(self) -> str:
        """Serialise every message as a JSON array using the wire field names."""
        return json.dumps([json.loads(m.to_json()) for m in self._messages], ensure_ascii=False)

    def as_text(self) -> str:
        """Render the whole exchange (including relays/interventions) for humans."""
        return "\n".join(self._line(m) for m in self._messages)

    def debate_text(self) -> str:
        """Render only the debaters' turns — the view the judge scores."""
        return "\n".join(self._line(m) for m in self._messages if m.type in _DEBATE_TYPES)

    def _line(self, m: Message) -> str:
        return (
            f"[r{m.round}] {_LABELS[m.sender]} -> {_LABELS[m.recipient]} "
            f"({m.type.value}): {m.payload.text}"
        )

    def _log(self, event: str, **fields: object) -> None:
        log = getattr(self._logger, "log", None)
        if callable(log):
            log(event, **fields)
