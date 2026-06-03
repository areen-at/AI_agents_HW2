"""Tests for the WebSearchTool query cache (Phase 8 follow-up).

Identical queries must be memoised so repeated per-side research in a debate
costs one live request (and one gatekeeper charge) instead of many; distinct
queries still fetch, and the cache can be disabled via config.
"""

from __future__ import annotations

import pytest

from debate.gatekeeper.limiter import Gatekeeper
from debate.tools import web_search
from debate.tools.web_search import WebSearchTool

_RAW = {"results": [{"title": "Barca", "url": "https://x.test/1", "content": "Won titles."}]}


class _FakeResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return _RAW


def _make_tool(**overrides: object) -> WebSearchTool:
    kwargs: dict = {
        "api_key": "secret-key",
        "max_results": 3,
        "request_seconds": 5,
        "allowed_domains": ["api.tavily.com"],
        "max_content_chars": 4000,
    }
    kwargs.update(overrides)
    return WebSearchTool(**kwargs)


def _counting_post(monkeypatch: pytest.MonkeyPatch) -> dict:
    calls = {"n": 0}

    def _post(*_a: object, **_k: object) -> _FakeResponse:
        calls["n"] += 1
        return _FakeResponse()

    monkeypatch.setattr(web_search.httpx, "post", _post)
    return calls


def _gate() -> Gatekeeper:
    return Gatekeeper(
        max_total_calls=80,
        max_total_usd=2.0,
        max_tokens_total=200000,
        cost_per_mtok_input=3.0,
        cost_per_mtok_output=15.0,
    )


def test_repeated_query_served_from_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _counting_post(monkeypatch)
    gate = _gate()
    tool = _make_tool(gatekeeper=gate)
    first = tool.search("barcelona")
    second = tool.search("barcelona")
    assert calls["n"] == 1  # second query never hits the network
    assert [c.url for c in first] == [c.url for c in second]
    assert gate.budget.calls == 1  # a cache hit is not charged


def test_distinct_queries_each_fetch(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _counting_post(monkeypatch)
    tool = _make_tool()
    tool.search("barcelona")
    tool.search("real madrid")
    assert calls["n"] == 2


def test_cache_can_be_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _counting_post(monkeypatch)
    tool = _make_tool(enable_cache=False)
    tool.search("barcelona")
    tool.search("barcelona")
    assert calls["n"] == 2
