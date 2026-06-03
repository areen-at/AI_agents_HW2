"""Tests for the provider-selection factory."""

from __future__ import annotations

import pytest

from debate.config.schema import Config
from debate.llm.base import Completion, LLMProvider
from debate.llm.factory import build_provider
from debate.llm.resilience import ResilientProvider


def _config(valid_config_dict: dict, provider: str) -> Config:
    valid_config_dict["llm"]["provider"] = provider
    return Config.model_validate(valid_config_dict)


def test_mock_provider_built_and_wrapped(valid_config_dict: dict) -> None:
    config = _config(valid_config_dict, "mock")
    provider = build_provider(config, model="mock-1")
    assert isinstance(provider, ResilientProvider)
    assert isinstance(provider, LLMProvider)
    result = provider.complete(
        "sys", [{"role": "user", "content": "hi"}], temperature=0.5, max_tokens=32
    )
    assert isinstance(result, Completion)


def test_real_provider_requires_secret(valid_config_dict: dict, monkeypatch) -> None:
    config = _config(valid_config_dict, "anthropic")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    from debate.config.secrets import MissingSecretError

    with pytest.raises(MissingSecretError):
        build_provider(config, model="claude")
