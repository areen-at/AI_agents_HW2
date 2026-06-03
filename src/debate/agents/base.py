"""BaseAgent — the shared foundation every agent stands on (PRD §2.3 / Phase 5).

Holds the resilient ``llm`` provider, the redacting ``logger``, typed ``config``,
an ``agent_id`` and a protocol ``role``. The single send pipeline builds the
system + user prompt, calls the LLM (already timeout/retry/gatekept), logs a
redacted line, and returns a validated :class:`~debate.protocol.message.Message`.
Subclasses supply only ``system_prompt`` and ``build_prompt`` — no other agent
duplicates the completion/logging/envelope plumbing.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..config.schema import Config
from ..llm.base import Completion, LLMProvider
from ..protocol.builder import build_message
from ..protocol.message import Citation, Message, MessageType, Meta, Party

_PREVIEW_CHARS = 120


class BaseAgent(ABC):
    """Abstract agent: owns the LLM/logger/config and the shared send pipeline."""

    def __init__(
        self,
        *,
        llm: LLMProvider,
        config: Config,
        agent_id: str,
        role: Party,
        temperature: float,
        logger: object | None = None,
    ) -> None:
        self.llm = llm
        self.config = config
        self.agent_id = agent_id
        self.role = role
        self._temperature = temperature
        self._logger = logger

    @abstractmethod
    def system_prompt(self) -> str:
        """Return the agent's system prompt (persona / rules)."""

    @abstractmethod
    def build_prompt(self, context: str) -> str:
        """Frame task ``context`` into the user-role prompt for this agent."""

    def send(
        self,
        *,
        recipient: Party,
        msg_type: MessageType,
        round: int,
        context: str,
        rebuts_message_id: str | None = None,
        citations: list[Citation] | None = None,
    ) -> Message:
        """Run one LLM turn and return it as a validated message envelope."""
        completion = self._complete(context)
        meta = Meta(
            tokens_used=completion.tokens_used,
            latency_ms=int(completion.latency_ms),
            model=completion.model,
        )
        return build_message(
            sender=self.role,
            recipient=recipient,
            type=msg_type,
            round=round,
            text=completion.text,
            rebuts_message_id=rebuts_message_id,
            citations=citations or [],
            meta=meta,
        )

    def _complete(self, context: str) -> Completion:
        """System + user prompt → LLM completion, with a redacted log line."""
        completion = self.llm.complete(
            self.system_prompt(),
            [{"role": "user", "content": self.build_prompt(context)}],
            temperature=self._temperature,
            max_tokens=self.config.llm.max_tokens,
        )
        self._log(
            "agent_turn",
            agent_id=self.agent_id,
            role=self.role.value,
            model=completion.model,
            tokens=completion.tokens_used,
            latency_ms=completion.latency_ms,
            preview=completion.text[:_PREVIEW_CHARS],
        )
        return completion

    def _log(self, event: str, **fields: object) -> None:
        log = getattr(self._logger, "log", None)
        if callable(log):
            log(event, **fields)
