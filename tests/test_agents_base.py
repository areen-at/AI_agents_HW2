"""Tests for :class:`BaseAgent` (Phase 5.2).

A minimal concrete subclass exercises the shared send pipeline: it must produce
a valid JSON envelope from a MockLLM turn, and every log line it emits must pass
through the redactor (a planted secret is masked, never written verbatim).
"""

from __future__ import annotations

from pathlib import Path

from debate.agents.base import BaseAgent
from debate.config.schema import Config
from debate.llm.mock import MockLLM
from debate.observability.fifo_logger import FifoLogger
from debate.observability.redaction import MASK
from debate.protocol.message import Message, MessageType, Party


class _TinyAgent(BaseAgent):
    def system_prompt(self) -> str:
        return "You are a test agent."

    def build_prompt(self, context: str) -> str:
        return f"Task: {context}"


def _make_agent(llm: MockLLM, config: Config, logger: object | None = None) -> _TinyAgent:
    return _TinyAgent(
        llm=llm,
        config=config,
        agent_id="tiny",
        role=Party.PRO,
        temperature=0.5,
        logger=logger,
    )


def test_send_produces_valid_envelope(valid_config_dict: dict) -> None:
    config = Config.model_validate(valid_config_dict)
    agent = _make_agent(MockLLM(["Hello from the mock."]), config)

    msg = agent.send(
        recipient=Party.JUDGE,
        msg_type=MessageType.ARGUMENT,
        round=1,
        context="argue",
    )

    assert isinstance(msg, Message)
    assert msg.sender is Party.PRO
    assert msg.recipient is Party.JUDGE
    assert msg.type is MessageType.ARGUMENT
    assert msg.payload.text == "Hello from the mock."
    # Round-trips through the wire format without loss.
    assert Message.from_json(msg.to_json()).message_id == msg.message_id


def test_complete_passes_temperature_and_max_tokens(valid_config_dict: dict) -> None:
    config = Config.model_validate(valid_config_dict)
    llm = MockLLM(["ok"])
    agent = _make_agent(llm, config)

    agent.send(recipient=Party.JUDGE, msg_type=MessageType.ARGUMENT, round=0, context="x")

    call = llm.calls[0]
    assert call["temperature"] == 0.5
    assert call["max_tokens"] == config.llm.max_tokens


def test_logs_are_redacted(tmp_path: Path, valid_config_dict: dict) -> None:
    config = Config.model_validate(valid_config_dict)
    logger = FifoLogger(tmp_path, max_files=5, max_lines_per_file=100)
    planted = "sk-ant-SUPERSECRETVALUE123456"
    agent = _make_agent(MockLLM([f"My key is {planted} ok"]), config, logger=logger)

    agent.send(recipient=Party.JUDGE, msg_type=MessageType.ARGUMENT, round=0, context="x")

    written = "\n".join(p.read_text(encoding="utf-8") for p in tmp_path.glob("*.jsonl"))
    assert planted not in written
    assert MASK in written
