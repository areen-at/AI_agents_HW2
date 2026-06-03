"""Tests for the config loader, schema validation, and secret resolution."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from debate.config.loader import load_config
from debate.config.schema import Config
from debate.config.secrets import MissingSecretError, get_secret, mask_secret


def test_loads_valid_config(config_file: Path) -> None:
    cfg = load_config(config_file, env_path=config_file.parent / ".env")
    assert isinstance(cfg, Config)
    assert cfg.debate.rounds_per_side == 10
    assert cfg.search.allowed_domains == ["api.tavily.com"]


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path / "nope.yaml")


def test_rejects_missing_required_key(valid_config_dict: dict) -> None:
    del valid_config_dict["debate"]["topic"]
    with pytest.raises(ValidationError):
        Config.model_validate(valid_config_dict)


def test_rejects_unknown_key(valid_config_dict: dict) -> None:
    valid_config_dict["debate"]["bogus"] = 1
    with pytest.raises(ValidationError):
        Config.model_validate(valid_config_dict)


def test_rejects_out_of_range_value(valid_config_dict: dict) -> None:
    valid_config_dict["debate"]["rounds_per_side"] = 0
    with pytest.raises(ValidationError):
        Config.model_validate(valid_config_dict)


def test_get_secret_reads_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-secret-value")
    assert get_secret("ANTHROPIC_API_KEY") == "sk-ant-secret-value"


def test_missing_secret_raises_without_leaking_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SEARCH_API_KEY", raising=False)
    with pytest.raises(MissingSecretError) as excinfo:
        get_secret("SEARCH_API_KEY")
    message = str(excinfo.value)
    assert "SEARCH_API_KEY" in message
    # The error names the variable but never an expected/actual value.
    assert "secret-value" not in message


def test_optional_secret_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert get_secret("OPENAI_API_KEY", required=False) is None


def test_mask_secret_hides_body() -> None:
    masked = mask_secret("sk-ant-abcdEFGH1234")
    assert masked == "sk-...1234"
    assert "abcdEFGH" not in masked
    assert mask_secret("tiny") == "***"
