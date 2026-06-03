"""Load ``config.yaml`` into a validated :class:`Config` object.

This is the single public entry point for configuration. It reads the YAML,
optionally loads a ``.env`` file into the environment (so secrets resolve), and
validates everything through the pydantic schema — failing fast on any problem.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .schema import Config

DEFAULT_CONFIG_PATH = Path("config.yaml")


def _load_dotenv(env_path: Path) -> None:
    """Populate ``os.environ`` from ``.env`` if python-dotenv is available.

    Optional and best-effort: a missing file or missing library is fine, since
    secrets may already be exported in the real environment.
    """
    if not env_path.exists():
        return
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(env_path, override=False)


def load_config(
    path: str | Path = DEFAULT_CONFIG_PATH,
    *,
    env_path: str | Path = ".env",
) -> Config:
    """Read, env-merge, and validate the configuration.

    Args:
        path: Path to the YAML config file.
        env_path: Path to a ``.env`` file to load before validation.

    Returns:
        A fully validated :class:`Config`.

    Raises:
        FileNotFoundError: if ``path`` does not exist.
        pydantic.ValidationError: if any value is missing/invalid.
    """
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    _load_dotenv(Path(env_path))

    raw: Any = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Config root must be a mapping, got {type(raw).__name__}")
    return Config.model_validate(raw)
