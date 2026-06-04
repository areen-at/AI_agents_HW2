"""Bootstrap helpers — assemble the SDK's collaborators from typed config.

Kept separate from :mod:`debate.sdk` so that module stays a thin facade: these
factories turn a :class:`~debate.config.schema.Config` into a FIFO logger, a
gatekeeper, and (for non-mock providers with a key present) the hardened
web-search tool. Secrets are resolved here, never echoed.
"""

from __future__ import annotations

from .config.schema import Config
from .config.secrets import get_secret
from .gatekeeper.limiter import Gatekeeper
from .observability.fifo_logger import FifoLogger
from .tools.web_search import WebSearchTool

_SEARCH_KEY_ENV = "SEARCH_API_KEY"


def build_logger(config: Config) -> FifoLogger:
    """Build the FIFO-rotation logger from the logging config section."""
    lg = config.logging
    return FifoLogger(
        lg.dir,
        max_files=lg.fifo_max_files,
        max_lines_per_file=lg.fifo_max_lines_per_file,
        level=lg.level,
    )


def build_gatekeeper(config: Config) -> Gatekeeper:
    """Build the spend/usage gatekeeper from the gatekeeper + cost config."""
    gk = config.gatekeeper
    return Gatekeeper(
        max_total_calls=gk.max_total_calls,
        max_total_usd=gk.max_total_usd,
        max_tokens_total=gk.max_tokens_total,
        cost_per_mtok_input=config.llm.cost_per_mtok_input,
        cost_per_mtok_output=config.llm.cost_per_mtok_output,
    )


def build_web(config: Config, gatekeeper: Gatekeeper, logger: object) -> WebSearchTool | None:
    """Build the search tool, or ``None`` for the mock provider / missing key."""
    if config.llm.provider == "mock":
        return None
    api_key = get_secret(_SEARCH_KEY_ENV, required=False)
    if not api_key:
        return None
    s = config.search
    return WebSearchTool(
        api_key=api_key,
        max_results=s.max_results,
        request_seconds=s.request_seconds,
        allowed_domains=s.allowed_domains,
        max_content_chars=config.security.max_external_content_chars,
        gatekeeper=gatekeeper,
        logger=logger,
        enable_cache=s.cache,
    )
