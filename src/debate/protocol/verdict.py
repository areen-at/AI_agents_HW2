"""The judge's verdict model with a hard **no-tie invariant** (PRD §6, §8).

Tie-prevention is enforced in code, not just the prompt: a verdict with equal
``pro``/``con`` scores (or a non pro/con winner) cannot be constructed. The
engine relies on this to guarantee a decisive outcome.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .message import Party


class Scores(BaseModel):
    """Differential persuasiveness scores; equality is rejected."""

    model_config = ConfigDict(extra="forbid")

    pro: float = Field(ge=0, le=100)
    con: float = Field(ge=0, le=100)

    @model_validator(mode="after")
    def _no_tie(self) -> Scores:
        if self.pro == self.con:
            raise ValueError(
                f"Tie forbidden: pro and con scores must differ (both were {self.pro})."
            )
        return self


class Verdict(BaseModel):
    """A decisive verdict: a single winner with a grounded rationale."""

    model_config = ConfigDict(extra="forbid")

    winner: Party
    scores: Scores
    rationale: str = Field(min_length=1)
    highlights: dict[str, list[str]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _winner_is_debater(self) -> Verdict:
        if self.winner is Party.JUDGE:
            raise ValueError("Winner must be 'pro' or 'con', never the judge.")
        return self

    @model_validator(mode="after")
    def _winner_matches_scores(self) -> Verdict:
        leader = Party.PRO if self.scores.pro > self.scores.con else Party.CON
        if self.winner is not leader:
            raise ValueError(
                f"Declared winner {self.winner.value!r} does not match the "
                f"higher score ({leader.value!r})."
            )
        return self
