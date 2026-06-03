"""Smoke tests for the terminal menu, driven by scripted stdin (Phase 7).

The menu is exercised with injected ``input_fn``/``output_fn`` so no real
keyboard or terminal is needed. We assert it runs a debate, shows the verdict
and transcript, survives a bad action, and exits cleanly.
"""

from __future__ import annotations

from collections.abc import Callable

from debate.agents.con_agent import ConAgent
from debate.agents.judge import JudgeAgent
from debate.agents.pro import ProAgent
from debate.config.schema import Config
from debate.llm.mock import MockLLM
from debate.orchestration.engine import Engine
from debate.sdk import DebateSDK
from debate.ui import menu

_VERDICT = '{"winner": "pro", "scores": {"pro": 77, "con": 50}, "rationale": "Pro led."}'


def _factory(config: Config) -> Engine:
    return Engine(
        judge=JudgeAgent(llm=MockLLM([_VERDICT]), config=config),
        pro=ProAgent(llm=MockLLM(), config=config),
        con=ConAgent(llm=MockLLM(), config=config),
        config=config,
    )


def _scripted(inputs: list[str]) -> Callable[[str], str]:
    queue = list(inputs)
    return lambda _prompt="": queue.pop(0)


def _drive(valid_config_dict: dict, inputs: list[str]) -> str:
    data = {**valid_config_dict, "debate": {**valid_config_dict["debate"], "rounds_per_side": 2}}
    sdk = DebateSDK(Config.model_validate(data), logger=object(), engine_factory=_factory)
    out: list[str] = []
    menu.run(sdk, input_fn=_scripted(inputs), output_fn=out.append)
    return "\n".join(out)


def test_run_then_view_verdict_and_exit(valid_config_dict: dict) -> None:
    out = _drive(valid_config_dict, ["2", "4", "0"])
    assert "WINNER: PRO" in out
    assert "Goodbye." in out


def test_transcript_and_settings(valid_config_dict: dict) -> None:
    out = _drive(valid_config_dict, ["2", "3", "5", "0"])
    assert "PRO -> JUDGE" in out
    assert "Provider:" in out


def test_configure_overrides_topic(valid_config_dict: dict) -> None:
    out = _drive(valid_config_dict, ["1", "Tea vs coffee", "", "2", "0"])
    assert "Tea vs coffee" in out


def test_unknown_option_is_reported(valid_config_dict: dict) -> None:
    out = _drive(valid_config_dict, ["9", "0"])
    assert "Unknown option" in out


def test_action_error_does_not_crash_menu(valid_config_dict: dict) -> None:
    # Viewing the verdict before any run raises; the menu must recover.
    out = _drive(valid_config_dict, ["4", "0"])
    assert "[error]" in out
    assert "Goodbye." in out
