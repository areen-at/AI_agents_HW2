"""The JSON message envelope exchanged between all agents (PRD §6).

Every inter-agent message is a :class:`Message`. ``from``/``to`` are Python
keywords, so they are modelled as ``sender``/``recipient`` with JSON aliases —
serialisation uses the wire names, while Python code uses safe attributes.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = "1.0"


class Party(StrEnum):
    PRO = "pro"
    CON = "con"
    JUDGE = "judge"


class MessageType(StrEnum):
    ARGUMENT = "argument"
    REBUTTAL = "rebuttal"
    RELAY = "relay"
    INTERVENTION = "intervention"
    VERDICT = "verdict"
    SYSTEM = "system"


class Citation(BaseModel):
    """A single web-search reference attached to an argument."""

    model_config = ConfigDict(extra="forbid")

    title: str
    url: str
    snippet: str = ""


class Payload(BaseModel):
    """Body of a message — the argument text plus mutual-response linkage."""

    model_config = ConfigDict(extra="forbid")

    text: str
    rebuts_message_id: str | None = None
    citations: list[Citation] = Field(default_factory=list)
    word_count: int = Field(default=0, ge=0)


class Meta(BaseModel):
    """Provider/runtime metadata recorded for observability."""

    model_config = ConfigDict(extra="forbid")

    tokens_used: int = Field(default=0, ge=0)
    latency_ms: int = Field(default=0, ge=0)
    model: str = ""


class Message(BaseModel):
    """A complete inter-agent JSON envelope."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_version: str = SCHEMA_VERSION
    message_id: str
    timestamp: str
    sender: Party = Field(alias="from")
    recipient: Party = Field(alias="to")
    type: MessageType
    round: int = Field(ge=0)
    payload: Payload
    meta: Meta = Field(default_factory=Meta)

    def to_json(self) -> str:
        """Serialise to a compact JSON string using the wire field names."""
        return self.model_dump_json(by_alias=True)

    @classmethod
    def from_json(cls, data: str) -> Message:
        """Parse a wire JSON string back into a validated :class:`Message`."""
        return cls.model_validate_json(data)
