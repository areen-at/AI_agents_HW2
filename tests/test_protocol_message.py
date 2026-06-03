"""Round-trip and validation tests for the JSON message envelope."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from debate.protocol.builder import build_message
from debate.protocol.message import Citation, Message, MessageType, Party


def test_round_trip_serialize_deserialize() -> None:
    msg = build_message(
        sender=Party.PRO,
        recipient=Party.JUDGE,
        type=MessageType.ARGUMENT,
        round=1,
        text="Barcelona has the better academy.",
        citations=[Citation(title="La Masia", url="https://example.com", snippet="x")],
    )
    wire = msg.to_json()
    restored = Message.from_json(wire)
    assert restored == msg
    assert restored.payload.word_count == 5


def test_wire_uses_from_and_to_aliases() -> None:
    msg = build_message(
        sender=Party.CON,
        recipient=Party.JUDGE,
        type=MessageType.REBUTTAL,
        round=2,
        text="Not so fast.",
    )
    data = json.loads(msg.to_json())
    assert data["from"] == "con"
    assert data["to"] == "judge"
    assert "sender" not in data


def test_builder_links_rebuttal() -> None:
    msg = build_message(
        sender=Party.CON,
        recipient=Party.JUDGE,
        type=MessageType.REBUTTAL,
        round=2,
        text="I disagree.",
        rebuts_message_id="abc-123",
    )
    assert msg.payload.rebuts_message_id == "abc-123"


def test_invalid_party_rejected() -> None:
    with pytest.raises(ValidationError):
        Message.model_validate(
            {
                "message_id": "1",
                "timestamp": "t",
                "from": "referee",
                "to": "judge",
                "type": "argument",
                "round": 1,
                "payload": {"text": "hi"},
            }
        )


def test_unknown_envelope_field_rejected() -> None:
    with pytest.raises(ValidationError):
        Message.model_validate(
            {
                "message_id": "1",
                "timestamp": "t",
                "from": "pro",
                "to": "judge",
                "type": "argument",
                "round": 1,
                "payload": {"text": "hi"},
                "extra": "boom",
            }
        )
