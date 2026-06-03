"""Shared pytest fixtures: a valid config dict and a temp config file."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def valid_config_dict() -> dict:
    """A complete, valid configuration mapping mirroring ``config.yaml``."""
    return {
        "llm": {
            "provider": "mock",
            "judge_model": "claude-opus-4-8",
            "debater_model": "claude-sonnet-4-6",
            "temperature": 0.8,
            "judge_temperature": 0.2,
            "max_tokens": 800,
            "cost_per_mtok_input": 3.0,
            "cost_per_mtok_output": 15.0,
        },
        "debate": {
            "topic": "Cats vs dogs",
            "rounds_per_side": 10,
            "max_words_per_turn": 150,
            "pro_skill": "evidence persuader",
            "con_skill": "emotional persuader",
        },
        "timeouts": {
            "request_seconds": 60,
            "retries": 2,
            "backoff_seconds": 2,
            "circuit_breaker_threshold": 3,
        },
        "watchdog": {"keepalive_seconds": 15, "max_restarts": 3},
        "gatekeeper": {
            "max_total_calls": 80,
            "max_total_usd": 2.0,
            "max_tokens_total": 200000,
        },
        "search": {
            "provider": "tavily",
            "max_results": 3,
            "request_seconds": 20,
            "allowed_domains": ["api.tavily.com"],
        },
        "logging": {
            "dir": "./logs",
            "fifo_max_files": 20,
            "fifo_max_lines_per_file": 500,
            "level": "INFO",
        },
        "security": {
            "max_external_content_chars": 4000,
            "enable_moderation": True,
            "banned_terms_file": None,
        },
    }


@pytest.fixture
def config_file(tmp_path: Path, valid_config_dict: dict) -> Iterator[Path]:
    """Write ``valid_config_dict`` to a temp YAML file and yield its path."""
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(valid_config_dict), encoding="utf-8")
    yield path
