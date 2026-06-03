"""Tests enforcing the no-tie invariant on the Verdict model."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from debate.protocol.message import Party
from debate.protocol.verdict import Scores, Verdict


def test_valid_differential_verdict_accepted() -> None:
    verdict = Verdict(
        winner=Party.PRO,
        scores=Scores(pro=80, con=70),
        rationale="Pro marshalled more vivid, concrete persuasion.",
    )
    assert verdict.winner is Party.PRO
    assert verdict.scores.pro > verdict.scores.con


def test_equal_scores_rejected() -> None:
    with pytest.raises(ValidationError):
        Scores(pro=75, con=75)


def test_judge_cannot_win() -> None:
    with pytest.raises(ValidationError):
        Verdict(
            winner=Party.JUDGE,
            scores=Scores(pro=80, con=70),
            rationale="invalid",
        )


def test_winner_must_match_higher_score() -> None:
    with pytest.raises(ValidationError):
        Verdict(
            winner=Party.CON,
            scores=Scores(pro=80, con=70),
            rationale="mismatched winner",
        )


def test_empty_rationale_rejected() -> None:
    with pytest.raises(ValidationError):
        Verdict(winner=Party.PRO, scores=Scores(pro=90, con=10), rationale="")
