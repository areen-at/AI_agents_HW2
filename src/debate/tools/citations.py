"""Citation model + tolerant parser for web-search results (PRD §3 / Phase 4).

A :class:`Citation` is the only shape search results take once they leave the
tool: a title, the source URL, and a snippet that has **already** passed through
the sanitizer. Parsing tolerates missing/malformed entries so a flaky provider
response degrades to fewer citations rather than raising mid-debate.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable

from pydantic import BaseModel, Field


class Citation(BaseModel):
    """A single sanitized search result handed to an agent."""

    title: str = Field(min_length=1)
    url: str = Field(min_length=1)
    snippet: str = ""


def parse_results(
    raw: Iterable[dict],
    *,
    sanitize: Callable[[str], str],
    max_results: int,
) -> list[Citation]:
    """Map raw provider result dicts to sanitized :class:`Citation` objects.

    Each snippet is run through ``sanitize`` before it can reach a model. Entries
    missing a title or url are skipped; the list is capped at ``max_results``.
    """
    citations: list[Citation] = []
    for item in raw:
        if len(citations) >= max_results:
            break
        title = (item.get("title") or "").strip()
        url = (item.get("url") or "").strip()
        if not title or not url:
            continue
        snippet = item.get("content") or item.get("snippet") or ""
        citations.append(Citation(title=title, url=url, snippet=sanitize(snippet)))
    return citations
