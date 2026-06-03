"""Hardened web-search tool — the mandatory internet capability (PRD §3 / Phase 4).

``WebSearchTool.search`` is the only path an agent uses to reach the internet.
Every request is vetted by the egress allowlist (anti-SSRF + HTTPS), counted by
the gatekeeper, bounded by a timeout, and every snippet returned is run through
the sanitizer so web text is treated as **data, never instructions**. Any
failure degrades to an empty result list (logged) so the debate continues.
"""

from __future__ import annotations

import httpx

from ..gatekeeper.budget import Usage
from ..gatekeeper.limiter import BudgetExceededError, Gatekeeper
from ..security import egress, sanitizer
from .citations import Citation, parse_results

_ENDPOINT = "https://api.tavily.com/search"
# Failures we contain and degrade to an empty result set (debate continues).
_DEGRADE = (
    egress.EgressError,
    BudgetExceededError,
    httpx.HTTPError,
    KeyError,
    ValueError,
)


class WebSearchTool:
    """Routes a query to the configured search API and returns sanitized citations."""

    def __init__(
        self,
        *,
        api_key: str,
        max_results: int,
        request_seconds: float,
        allowed_domains: list[str],
        max_content_chars: int,
        endpoint: str = _ENDPOINT,
        gatekeeper: Gatekeeper | None = None,
        logger: object | None = None,
    ) -> None:
        self._api_key = api_key
        self._max_results = max_results
        self._timeout = request_seconds
        self._allowed = allowed_domains
        self._max_chars = max_content_chars
        self._endpoint = endpoint
        self._gatekeeper = gatekeeper
        self._logger = logger

    def search(self, query: str) -> list[Citation]:
        """Return up to ``max_results`` sanitized citations; ``[]`` on any failure."""
        try:
            egress.validate_url(self._endpoint, allowed_domains=self._allowed)
            if self._gatekeeper is not None:
                self._gatekeeper.check(Usage(calls=1))
            raw = self._fetch(query)
        except _DEGRADE as exc:
            self._log("web_search_failed", query=query, error=str(exc))
            return []
        if self._gatekeeper is not None:
            self._gatekeeper.record(Usage(calls=1))
        citations = parse_results(raw, sanitize=self._sanitize, max_results=self._max_results)
        self._log("web_search_ok", query=query, results=len(citations))
        return citations

    def _fetch(self, query: str) -> list[dict]:
        """Perform the vetted HTTPS request and return the raw result list."""
        payload = {"query": query, "max_results": self._max_results}
        headers = {"Authorization": f"Bearer {self._api_key}"}
        resp = httpx.post(self._endpoint, json=payload, headers=headers, timeout=self._timeout)
        resp.raise_for_status()
        return resp.json().get("results", [])

    def _sanitize(self, text: str) -> str:
        return sanitizer.sanitize(text, max_chars=self._max_chars)

    def _log(self, event: str, **fields: object) -> None:
        log = getattr(self._logger, "log", None)
        if callable(log):
            log(event, **fields)
