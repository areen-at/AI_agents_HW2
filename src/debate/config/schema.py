"""Typed, validated configuration models (one per ``config.yaml`` section).

Every field carries a range/type constraint and unknown keys are rejected, so
a malformed config fails fast at load time rather than mid-debate.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Provider = Literal["anthropic", "openai", "groq", "mock"]


class _Strict(BaseModel):
    """Base model that forbids unknown keys (typo-proof config)."""

    model_config = ConfigDict(extra="forbid")


class LLMConfig(_Strict):
    provider: Provider = "anthropic"
    judge_model: str = Field(min_length=1)
    debater_model: str = Field(min_length=1)
    temperature: float = Field(ge=0.0, le=2.0)
    judge_temperature: float = Field(ge=0.0, le=2.0)
    max_tokens: int = Field(gt=0)
    cost_per_mtok_input: float = Field(ge=0.0)
    cost_per_mtok_output: float = Field(ge=0.0)


class DebateConfig(_Strict):
    topic: str = Field(min_length=1)
    rounds_per_side: int = Field(ge=1)
    max_words_per_turn: int = Field(gt=0)
    pro_skill: str = Field(min_length=1)
    con_skill: str = Field(min_length=1)


class TimeoutsConfig(_Strict):
    request_seconds: float = Field(gt=0)
    retries: int = Field(ge=0)
    backoff_seconds: float = Field(ge=0)
    circuit_breaker_threshold: int = Field(ge=1)


class WatchdogConfig(_Strict):
    keepalive_seconds: float = Field(gt=0)
    max_restarts: int = Field(ge=0)


class GatekeeperConfig(_Strict):
    max_total_calls: int = Field(gt=0)
    max_total_usd: float = Field(gt=0)
    max_tokens_total: int = Field(gt=0)


class SearchConfig(_Strict):
    provider: str = Field(min_length=1)
    max_results: int = Field(gt=0)
    request_seconds: float = Field(gt=0)
    allowed_domains: list[str] = Field(min_length=1)


class LoggingConfig(_Strict):
    dir: str = Field(min_length=1)
    fifo_max_files: int = Field(gt=0)
    fifo_max_lines_per_file: int = Field(gt=0)
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"


class SecurityConfig(_Strict):
    max_external_content_chars: int = Field(gt=0)
    enable_moderation: bool = True
    banned_terms_file: str | None = None


class Config(_Strict):
    """Root configuration object — the single typed source of truth."""

    llm: LLMConfig
    debate: DebateConfig
    timeouts: TimeoutsConfig
    watchdog: WatchdogConfig
    gatekeeper: GatekeeperConfig
    search: SearchConfig
    logging: LoggingConfig
    security: SecurityConfig
