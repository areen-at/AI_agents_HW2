"""Helpers to construct message envelopes with generated ids/timestamps.

Centralising id and timestamp generation keeps every call site consistent and
makes the rest of the code free of ``uuid``/``datetime`` boilerplate.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from .message import Citation, Message, MessageType, Meta, Party, Payload


def new_message_id() -> str:
    """Return a fresh unique message id."""
    return str(uuid.uuid4())


def utc_timestamp() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(UTC).isoformat()


def build_message(
    *,
    sender: Party,
    recipient: Party,
    type: MessageType,
    round: int,
    text: str,
    rebuts_message_id: str | None = None,
    citations: list[Citation] | None = None,
    word_count: int | None = None,
    meta: Meta | None = None,
) -> Message:
    """Construct a validated :class:`Message`, filling id/timestamp/word_count.

    ``word_count`` defaults to the number of whitespace-separated tokens in
    ``text`` when not supplied, so callers cannot forget it.
    """
    payload = Payload(
        text=text,
        rebuts_message_id=rebuts_message_id,
        citations=citations or [],
        word_count=word_count if word_count is not None else len(text.split()),
    )
    return Message(
        message_id=new_message_id(),
        timestamp=utc_timestamp(),
        sender=sender,
        recipient=recipient,
        type=type,
        round=round,
        payload=payload,
        meta=meta or Meta(),
    )
