"""Tests for the orchestration engine and Child→Father→Child routing (Phase 6).

A full MockLLM debate must: route every debater turn through the judge (no
direct Pro↔Con traffic), link each rebuttal to the relay it answers (mutual
response), produce exactly ``rounds_per_side`` turns per debater, and end in a
decisive, never-tied verdict.
"""

from __future__ import annotations

from debate.agents.con_agent import ConAgent
from debate.agents.judge import JudgeAgent
from debate.agents.pro import ProAgent
from debate.config.schema import Config
from debate.llm.mock import MockLLM
from debate.orchestration.engine import DebateResult, Engine
from debate.protocol.message import MessageType, Party

_VERDICT = '{"winner": "pro", "scores": {"pro": 61, "con": 40}, "rationale": "Pro led."}'


def _engine(valid_config_dict: dict, *, rounds: int) -> Engine:
    data = {
        **valid_config_dict,
        "debate": {**valid_config_dict["debate"], "rounds_per_side": rounds},
    }
    config = Config.model_validate(data)
    pro = ProAgent(llm=MockLLM(), config=config)
    con = ConAgent(llm=MockLLM(), config=config)
    judge = JudgeAgent(llm=MockLLM([_VERDICT]), config=config)
    return Engine(judge=judge, pro=pro, con=con, config=config)


def _run(valid_config_dict: dict, *, rounds: int = 3) -> DebateResult:
    return _engine(valid_config_dict, rounds=rounds).run()


def test_no_direct_pro_con_traffic(valid_config_dict: dict) -> None:
    result = _run(valid_config_dict)
    for msg in result.transcript.messages:
        if msg.sender in (Party.PRO, Party.CON):
            assert msg.recipient is Party.JUDGE
        if msg.recipient in (Party.PRO, Party.CON):
            assert msg.sender is Party.JUDGE


def test_exactly_rounds_per_side_turns_each(valid_config_dict: dict) -> None:
    rounds = 4
    result = _run(valid_config_dict, rounds=rounds)
    assert result.transcript.count_turns(Party.PRO) == rounds
    assert result.transcript.count_turns(Party.CON) == rounds


def test_rebuttals_link_the_relay_they_answer(valid_config_dict: dict) -> None:
    result = _run(valid_config_dict)
    messages = result.transcript.messages
    # Relays delivered to each debater, keyed by recipient.
    relays_to = {Party.PRO: set(), Party.CON: set()}
    for msg in messages:
        if msg.type is MessageType.RELAY:
            relays_to[msg.recipient].add(msg.message_id)
    for msg in messages:
        if msg.type is MessageType.REBUTTAL:
            assert msg.payload.rebuts_message_id in relays_to[msg.sender]


def test_first_pro_turn_opens_then_rebuts(valid_config_dict: dict) -> None:
    result = _run(valid_config_dict)
    pro_turns = [
        m
        for m in result.transcript.messages
        if m.sender is Party.PRO and m.type in (MessageType.ARGUMENT, MessageType.REBUTTAL)
    ]
    assert pro_turns[0].type is MessageType.ARGUMENT
    assert all(m.type is MessageType.REBUTTAL for m in pro_turns[1:])
    # Con always answers, so every Con turn is a rebuttal.
    con_turns = [m for m in result.transcript.messages if m.sender is Party.CON]
    assert all(m.type is MessageType.REBUTTAL for m in con_turns)


def test_verdict_is_decisive(valid_config_dict: dict) -> None:
    result = _run(valid_config_dict)
    assert result.verdict.winner is Party.PRO
    assert result.verdict.scores.pro != result.verdict.scores.con


def test_transcript_exports_json_and_text(valid_config_dict: dict) -> None:
    result = _run(valid_config_dict, rounds=2)
    assert result.transcript.as_json().startswith("[")
    assert "PRO -> JUDGE" in result.transcript.as_text()
    assert "JUDGE -> CON (relay)" in result.transcript.as_text()
    # debate_text carries only the debaters' turns (no relays / interventions).
    assert "(relay)" not in result.transcript.debate_text()
