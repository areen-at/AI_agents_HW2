"""Provider selection: build a resilient provider from typed config.

Reads ``llm.provider`` and returns the chosen backend already wrapped in
:class:`~debate.llm.resilience.ResilientProvider`, so callers always get the
timeout/retry/breaker/gatekeeper choke-point. Vendor SDK modules are imported
lazily inside each branch so unselected providers need not be installed.
"""

from __future__ import annotations

from ..config.schema import Config
from ..config.secrets import get_secret
from ..gatekeeper.limiter import Gatekeeper
from .base import LLMProvider
from .mock import MockLLM
from .resilience import ResilientProvider

_KEY_ENV = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY"}


def build_provider(
    config: Config,
    *,
    model: str,
    gatekeeper: Gatekeeper | None = None,
    logger: object | None = None,
) -> LLMProvider:
    """Build the configured provider for ``model``, wrapped for resilience."""
    raw = _raw_provider(config, model)
    t = config.timeouts
    return ResilientProvider(
        raw,
        request_seconds=t.request_seconds,
        retries=t.retries,
        backoff_seconds=t.backoff_seconds,
        breaker_threshold=t.circuit_breaker_threshold,
        gatekeeper=gatekeeper,
        logger=logger,
    )


def _raw_provider(config: Config, model: str) -> LLMProvider:
    provider = config.llm.provider
    if provider == "mock":
        return MockLLM(model=model)
    api_key = get_secret(_KEY_ENV[provider]) or ""  # get_secret raises if missing
    request_seconds = config.timeouts.request_seconds
    if provider == "anthropic":
        from .anthropic import AnthropicProvider

        return AnthropicProvider(api_key=api_key, model=model, request_seconds=request_seconds)
    from .openai import OpenAIProvider

    return OpenAIProvider(api_key=api_key, model=model, request_seconds=request_seconds)
