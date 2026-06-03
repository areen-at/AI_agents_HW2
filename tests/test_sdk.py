"""Tests for the interface-agnostic DebateSDK (Phase 7).

A full MockLLM debate driven through the SDK must yield a decisive verdict and
the correct per-side turn count, expose transcript/verdict accessors, honour
topic/round overrides, and never reach the network (mock provider).
"""

from __future__ import annotations

import pytest

from debate.agents.con_agent import ConAgent
from debate.agents.judge import JudgeAgent
from debate.agents.pro import ProAgent
from debate.config.schema import Config
from debate.llm.mock import MockLLM
from debate.orchestration.engine import Engine
from debate.protocol.message import Party
from debate.sdk import DebateSDK

_VERDICT = '{"winner": "con", "scores": {"pro": 41, "con": 72}, "rationale": "Con led."}'


def _factory(config: Config) -> Engine:
    return Engine(
        judge=JudgeAgent(llm=MockLLM([_VERDICT]), config=config),
        pro=ProAgent(llm=MockLLM(), config=config),
        con=ConAgent(llm=MockLLM(), config=config),
        config=config,
    )


def _sdk(valid_config_dict: dict) -> DebateSDK:
    config = Config.model_validate(valid_config_dict)
    return DebateSDK(config, logger=object(), engine_factory=_factory)


def test_run_debate_is_decisive_with_correct_counts(valid_config_dict: dict) -> None:
    sdk = _sdk(valid_config_dict)
    result = sdk.run_debate(rounds=3)
    assert result.verdict.winner is Party.CON
    assert result.verdict.scores.pro != result.verdict.scores.con
    assert result.transcript.count_turns(Party.PRO) == 3
    assert result.transcript.count_turns(Party.CON) == 3


def test_accessors_expose_last_result(valid_config_dict: dict) -> None:
    sdk = _sdk(valid_config_dict)
    sdk.run_debate(rounds=2)
    assert sdk.result is not None
    assert sdk.verdict.winner is Party.CON
    assert sdk.transcript.as_json().startswith("[")


def test_accessors_raise_before_any_run(valid_config_dict: dict) -> None:
    sdk = _sdk(valid_config_dict)
    with pytest.raises(RuntimeError):
        _ = sdk.verdict


def test_topic_override_does_not_mutate_base_config(valid_config_dict: dict) -> None:
    config = Config.model_validate(valid_config_dict)
    captured: list[str] = []

    def factory(cfg: Config) -> Engine:
        captured.append(cfg.debate.topic)
        return _factory(cfg)

    sdk = DebateSDK(config, logger=object(), engine_factory=factory)
    sdk.run_debate(topic="Tea vs coffee", rounds=1)
    assert captured == ["Tea vs coffee"]
    assert sdk.config.debate.topic == valid_config_dict["debate"]["topic"]


def test_no_override_reuses_config_topic(valid_config_dict: dict) -> None:
    sdk = _sdk(valid_config_dict)
    result = sdk.run_debate(rounds=1)
    assert result.transcript.count_turns(Party.PRO) == 1
