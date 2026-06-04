"""DebateSDK — the interface-agnostic public API (Phase 7).

A single entry point that assembles the whole debate stack from a
:class:`~debate.config.schema.Config` — a FIFO logger, the gatekeeper, an
optional hardened web-search tool, and the routed :class:`Engine` — and runs a
debate. The terminal menu, the human tester, and the agent itself all drive
*only* this class, so behaviour is identical regardless of interface (PRD §2.2).
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from .bootstrap import build_gatekeeper, build_logger, build_web
from .config.loader import DEFAULT_CONFIG_PATH, load_config
from .config.schema import Config
from .gatekeeper.limiter import Gatekeeper
from .orchestration.engine import DebateResult, Engine
from .protocol.verdict import Verdict
from .tools.web_search import WebSearchTool

EngineFactory = Callable[[Config], Engine]


class DebateSDK:
    """Builds and runs debates from configuration, independent of any UI."""

    def __init__(
        self,
        config: Config,
        *,
        logger: object | None = None,
        gatekeeper: Gatekeeper | None = None,
        web: WebSearchTool | None = None,
        engine_factory: EngineFactory | None = None,
    ) -> None:
        self._config = config
        self._logger = logger if logger is not None else build_logger(config)
        self._gatekeeper = gatekeeper or build_gatekeeper(config)
        self._web = web if web is not None else build_web(config, self._gatekeeper, self._logger)
        self._engine_factory = engine_factory or self._default_engine
        self._result: DebateResult | None = None

    @classmethod
    def from_path(
        cls,
        path: str | Path = DEFAULT_CONFIG_PATH,
        *,
        env_path: str | Path = ".env",
    ) -> DebateSDK:
        """Construct an SDK by loading and validating a config file."""
        return cls(load_config(path, env_path=env_path))

    @property
    def config(self) -> Config:
        """The active configuration object."""
        return self._config

    @property
    def result(self) -> DebateResult | None:
        """The most recent debate result, or ``None`` before any run."""
        return self._result

    @property
    def transcript(self) -> object:
        """The most recent debate's transcript (after a run)."""
        return self._require_result().transcript

    @property
    def verdict(self) -> Verdict:
        """The most recent debate's decisive verdict (after a run)."""
        return self._require_result().verdict

    def run_debate(
        self,
        *,
        topic: str | None = None,
        rounds: int | None = None,
    ) -> DebateResult:
        """Run one full debate, optionally overriding topic/rounds for this run."""
        config = self._with_overrides(topic, rounds)
        self._log(
            "debate_start",
            topic=config.debate.topic,
            rounds=config.debate.rounds_per_side,
        )
        self._result = self._engine_factory(config).run()
        return self._result

    def _default_engine(self, config: Config) -> Engine:
        return Engine.from_config(
            config, gatekeeper=self._gatekeeper, logger=self._logger, web=self._web
        )

    def _with_overrides(self, topic: str | None, rounds: int | None) -> Config:
        pairs = (("topic", topic), ("rounds_per_side", rounds))
        updates = {k: v for k, v in pairs if v is not None}
        if not updates:
            return self._config
        debate = self._config.debate.model_copy(update=updates)
        return self._config.model_copy(update={"debate": debate})

    def _require_result(self) -> DebateResult:
        if self._result is None:
            raise RuntimeError("No debate has been run yet; call run_debate() first.")
        return self._result

    def _log(self, event: str, **fields: object) -> None:
        log = getattr(self._logger, "log", None)
        if callable(log):
            log(event, **fields)
