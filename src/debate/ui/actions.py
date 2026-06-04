"""Menu actions — map each menu choice to a DebateSDK call and a rendering.

The :class:`Actions` object holds the SDK plus any pending topic/round
overrides the user has configured. Every method returns the text to display;
the :mod:`debate.ui.menu` module owns all I/O. Keeping the wiring here makes
the actions unit-testable without a terminal.
"""

from __future__ import annotations

from ..config.schema import Config
from ..protocol.verdict import Verdict
from ..sdk import DebateSDK


class Actions:
    """Stateful adapter between menu choices and the SDK."""

    def __init__(self, sdk: DebateSDK) -> None:
        self._sdk = sdk
        self._topic: str | None = None
        self._rounds: int | None = None

    def configure(self, topic: str, rounds: str) -> str:
        """Record optional topic/round overrides for the next run."""
        if topic.strip():
            self._topic = topic.strip()
        if rounds.strip():
            value = int(rounds)
            if value < 1:
                raise ValueError("rounds per side must be >= 1")
            self._rounds = value
        return (
            f"Configured: topic={self._topic or '(config default)'}, "
            f"rounds={self._rounds or '(config default)'}"
        )

    def run(self) -> str:
        """Run a full debate with any pending overrides and show the verdict."""
        result = self._sdk.run_debate(topic=self._topic, rounds=self._rounds)
        return "Debate complete.\n" + render_verdict(result.verdict)

    def transcript(self) -> str:
        """Render the most recent debate transcript for humans."""
        return self._sdk.transcript.as_text()

    def verdict(self) -> str:
        """Render the most recent decisive verdict."""
        return render_verdict(self._sdk.verdict)

    def settings(self) -> str:
        """Show the active, secret-free configuration summary."""
        return render_settings(self._sdk.config)


def render_verdict(verdict: Verdict) -> str:
    """Format a verdict (winner, differential scores, rationale)."""
    lines = [
        f"WINNER: {verdict.winner.value.upper()}",
        f"Scores: pro={verdict.scores.pro}  con={verdict.scores.con}",
        f"Rationale: {verdict.rationale}",
    ]
    return "\n".join(lines)


def render_settings(config: Config) -> str:
    """Summarise the key tunables without ever printing a secret."""
    lines = [
        f"Provider:        {config.llm.provider}",
        f"Judge model:     {config.llm.judge_model}",
        f"Debater model:   {config.llm.debater_model}",
        f"Topic:           {config.debate.topic}",
        f"Rounds per side: {config.debate.rounds_per_side}",
        f"Max words/turn:  {config.debate.max_words_per_turn}",
        f"Budget (USD):    {config.gatekeeper.max_total_usd}",
        f"Max calls:       {config.gatekeeper.max_total_calls}",
    ]
    return "\n".join(lines)
