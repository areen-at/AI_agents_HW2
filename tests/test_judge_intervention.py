"""Tests for :class:`JudgeAgent` (Phase 5.5).

The judge must detect over-agreement (anti-agreement duty), relay messages to the
opposite party, and always return a decisive verdict — including breaking a tie in
code when the model hands back equal scores.
"""

from __future__ import annotations

from debate.agents.judge import JudgeAgent
from debate.config.schema import Config
from debate.llm.mock import OVER_AGREEMENT_TEXT, MockLLM, tie_verdict_json
from debate.protocol.builder import build_message
from debate.protocol.message import MessageType, Party


def _judge(llm: MockLLM, config_dict: dict) -> JudgeAgent:
    return JudgeAgent(llm=llm, config=Config.model_validate(config_dict))


def test_should_intervene_on_over_agreement(valid_config_dict: dict) -> None:
    assert JudgeAgent.should_intervene("I totally agree with you.") is True
    assert JudgeAgent.should_intervene(OVER_AGREEMENT_TEXT) is True
    assert JudgeAgent.should_intervene("You are absolutely right about that.") is True


def test_does_not_intervene_on_a_normal_argument(valid_config_dict: dict) -> None:
    text = "Cats are independent, low-maintenance, and clearly the superior pet."
    assert JudgeAgent.should_intervene(text) is False


def test_intervene_produces_intervention_message(valid_config_dict: dict) -> None:
    judge = _judge(MockLLM(["Stay in character and defend your side."]), valid_config_dict)
    msg = judge.intervene(Party.PRO, reason="over-agreement", round=2)
    assert msg.type is MessageType.INTERVENTION
    assert msg.sender is Party.JUDGE
    assert msg.recipient is Party.PRO


def test_relay_forwards_to_opponent(valid_config_dict: dict) -> None:
    judge = _judge(MockLLM(), valid_config_dict)
    argument = build_message(
        sender=Party.PRO,
        recipient=Party.JUDGE,
        type=MessageType.ARGUMENT,
        round=1,
        text="Cats win.",
    )
    relayed = judge.relay(argument, round=1)
    assert relayed.sender is Party.JUDGE
    assert relayed.recipient is Party.CON
    assert relayed.type is MessageType.RELAY
    assert relayed.payload.rebuts_message_id == argument.message_id
    assert relayed.payload.text == "Cats win."


def test_verdict_breaks_a_tie(valid_config_dict: dict) -> None:
    judge = _judge(MockLLM([tie_verdict_json(score=7)]), valid_config_dict)
    verdict = judge.verdict("...transcript...")
    assert verdict.scores.pro != verdict.scores.con
    assert verdict.winner is Party.PRO  # declared winner kept after tie-break


def test_verdict_parses_differential_scores(valid_config_dict: dict) -> None:
    payload = '{"winner": "con", "scores": {"pro": 40, "con": 61}, "rationale": "Stronger."}'
    judge = _judge(MockLLM([payload]), valid_config_dict)
    verdict = judge.verdict("...transcript...")
    assert verdict.winner is Party.CON
    assert verdict.scores.con == 61
    assert verdict.scores.pro == 40
