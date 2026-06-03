"""JudgeAgent — the topic-blind father node: relay, intervene, decisive verdict.

The judge never takes a side on the motion; it scores only *persuasiveness*. It
relays each debater turn to the opponent (child → father → child), intervenes
when a debater starts to agree/concede, and renders a verdict whose scores are
forced to differ — a tie is broken in code so the no-tie invariant in
:class:`~debate.protocol.verdict.Verdict` can never trip.
"""

from __future__ import annotations

import json
import re

from ..config.schema import Config
from ..llm.base import LLMProvider
from ..prompts.loader import load_prompt
from ..protocol.builder import build_message
from ..protocol.message import Message, MessageType, Party
from ..protocol.verdict import Scores, Verdict
from .base import BaseAgent

_TIE_BREAK_DELTA = 0.5
# Phrases that betray people-pleasing / conceding — the judge must intervene.
_AGREE_RE = re.compile(
    r"\b(?:i (?:completely |totally |fully |whole[- ]?heartedly )?agree"
    r"|you(?:'re| are) (?:absolutely |completely )?right"
    r"|i concede|i give up|you win|you have a (?:good |fair )?point)\b",
    flags=re.IGNORECASE,
)


class JudgeAgent(BaseAgent):
    """Routes messages, polices over-agreement, and issues the final verdict."""

    def __init__(
        self,
        *,
        llm: LLMProvider,
        config: Config,
        logger: object | None = None,
    ) -> None:
        super().__init__(
            llm=llm,
            config=config,
            agent_id="judge",
            role=Party.JUDGE,
            temperature=config.llm.judge_temperature,
            logger=logger,
        )

    def system_prompt(self) -> str:
        return load_prompt("judge")

    def build_prompt(self, context: str) -> str:
        return (
            f"{context}\n\n[Reminder: you are topic-blind. Score persuasiveness, "
            "not truth. A tie is never allowed.]"
        )

    @staticmethod
    def should_intervene(text: str) -> bool:
        """True when ``text`` shows a debater agreeing/conceding (anti-agreement)."""
        return _AGREE_RE.search(text) is not None

    def relay(self, msg: Message, round: int) -> Message:
        """Forward a debater's message to the opponent (routing, no model call)."""
        opponent = Party.CON if msg.sender is Party.PRO else Party.PRO
        return build_message(
            sender=Party.JUDGE,
            recipient=opponent,
            type=MessageType.RELAY,
            round=round,
            text=msg.payload.text,
            rebuts_message_id=msg.message_id,
            citations=list(msg.payload.citations),
        )

    def intervene(self, recipient: Party, reason: str, round: int) -> Message:
        """Emit an anti-agreement reminder of the debater's adversarial role."""
        self._log("judge_intervene", recipient=recipient.value, reason=reason)
        context = (
            "A debater is conceding or agreeing with the opponent. Remind them, "
            f"firmly and briefly, to defend their assigned side. Reason: {reason}"
        )
        return self.send(
            recipient=recipient,
            msg_type=MessageType.INTERVENTION,
            round=round,
            context=context,
        )

    def verdict(self, transcript: str) -> Verdict:
        """Score the debate and return a decisive (never-tied) verdict."""
        context = (
            "Here is the full debate transcript. Decide who argued more "
            "persuasively and return ONLY a JSON object with keys "
            '"winner" ("pro"|"con"), "scores" {"pro": <0-100>, "con": <0-100>}, '
            f'"rationale", "highlights".\n\nTRANSCRIPT:\n{transcript}'
        )
        completion = self._complete(context)
        return self._parse_verdict(completion.text)

    def _parse_verdict(self, text: str) -> Verdict:
        """Parse model JSON into a Verdict, breaking any tie in code."""
        data = json.loads(_extract_json(text))
        pro = float(data["scores"]["pro"])
        con = float(data["scores"]["con"])
        pro, con = _break_tie(pro, con, str(data.get("winner", "")).lower())
        highlights = data.get("highlights")
        return Verdict(
            winner=Party.PRO if pro > con else Party.CON,
            scores=Scores(pro=pro, con=con),
            rationale=str(data.get("rationale") or "No rationale provided."),
            highlights=highlights if isinstance(highlights, dict) else {},
        )


def _extract_json(text: str) -> str:
    """Return the first ``{...}`` block so stray prose around JSON is tolerated."""
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("no JSON object found in verdict response")
    return text[start : end + 1]


def _break_tie(pro: float, con: float, declared: str) -> tuple[float, float]:
    """Nudge equal scores apart (staying in [0, 100]), honouring the declared side."""
    if pro != con:
        return pro, con
    if declared == "con":
        if con + _TIE_BREAK_DELTA <= 100:
            return pro, con + _TIE_BREAK_DELTA
        return pro - _TIE_BREAK_DELTA, con
    if pro + _TIE_BREAK_DELTA <= 100:
        return pro + _TIE_BREAK_DELTA, con
    return pro, con - _TIE_BREAK_DELTA
