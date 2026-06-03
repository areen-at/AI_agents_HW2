"""Engine — the thin debate coordinator (Phase 6.4).

Wires a Judge + Pro + Con (from config), loops ``rounds_per_side`` exchanges
through the :class:`Round` runner, and closes with the judge's decisive verdict.
Every turn — debater turns *and* the final verdict — is guarded by the
:class:`Watchdog`. Construct directly with pre-built agents (tests) or via
:meth:`from_config`, which builds resilient, gatekept providers through the
factory choke-point.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..agents.con_agent import ConAgent
from ..agents.judge import JudgeAgent
from ..agents.pro import ProAgent
from ..config.schema import Config
from ..gatekeeper.limiter import BudgetExceededError, Gatekeeper
from ..llm.factory import build_provider
from ..protocol.verdict import Verdict
from ..tools.web_search import WebSearchTool
from .round import Round
from .router import Router
from .transcript import Transcript
from .watchdog import Watchdog


@dataclass(frozen=True)
class DebateResult:
    """The outcome of a full debate: its transcript and the judge's verdict."""

    transcript: Transcript
    verdict: Verdict


class Engine:
    """Coordinates the routed debate loop and the closing verdict."""

    def __init__(
        self,
        *,
        judge: JudgeAgent,
        pro: ProAgent,
        con: ConAgent,
        config: Config,
        watchdog: Watchdog | None = None,
        logger: object | None = None,
    ) -> None:
        self._judge = judge
        self._pro = pro
        self._con = con
        self._config = config
        self._logger = logger
        self._watchdog = watchdog or Watchdog(
            keepalive_seconds=config.watchdog.keepalive_seconds,
            max_restarts=config.watchdog.max_restarts,
            logger=logger,
            fatal=(BudgetExceededError,),
        )

    @classmethod
    def from_config(
        cls,
        config: Config,
        *,
        gatekeeper: Gatekeeper | None = None,
        logger: object | None = None,
        web: WebSearchTool | None = None,
    ) -> Engine:
        """Build the judge and both debaters from config (resilient providers)."""

        def provider(model: str) -> object:
            return build_provider(config, model=model, gatekeeper=gatekeeper, logger=logger)

        judge = JudgeAgent(llm=provider(config.llm.judge_model), config=config, logger=logger)
        debater = config.llm.debater_model
        pro = ProAgent(llm=provider(debater), config=config, web=web, logger=logger)
        con = ConAgent(llm=provider(debater), config=config, web=web, logger=logger)
        return cls(judge=judge, pro=pro, con=con, config=config, logger=logger)

    def run(self) -> DebateResult:
        """Play every round, then return the transcript and decisive verdict."""
        transcript = Transcript(logger=self._logger)
        router = Router(self._judge, logger=self._logger)
        rounds = Round(
            pro=self._pro,
            con=self._con,
            router=router,
            transcript=transcript,
            guard=self._watchdog.run,
            topic=self._config.debate.topic,
        )
        for number in range(1, self._config.debate.rounds_per_side + 1):
            rounds.play(number)
        text = transcript.debate_text()
        verdict = self._watchdog.run("verdict", lambda: self._judge.verdict(text))
        self._log(
            "debate_complete",
            winner=verdict.winner.value,
            pro=verdict.scores.pro,
            con=verdict.scores.con,
        )
        return DebateResult(transcript=transcript, verdict=verdict)

    def _log(self, event: str, **fields: object) -> None:
        log = getattr(self._logger, "log", None)
        if callable(log):
            log(event, **fields)
