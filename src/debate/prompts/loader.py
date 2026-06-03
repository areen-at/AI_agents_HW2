"""Load named prompt templates (assets) that live beside this module.

Prompts are kept as ``.md`` files so agent logic stays tiny and the prompts
themselves remain reviewable/diffable on their own. :func:`render_prompt`
substitutes ``{placeholder}`` tokens via plain replacement (not ``str.format``)
so markdown braces in a template can never trigger a formatting error.
"""

from __future__ import annotations

from pathlib import Path

_DIR = Path(__file__).resolve().parent


def load_prompt(name: str) -> str:
    """Return the raw text of the ``<name>.md`` template in this package."""
    path = _DIR / f"{name}.md"
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"unknown prompt template: {name!r}") from exc


def render_prompt(name: str, /, **values: str) -> str:
    """Load ``name`` and replace each ``{key}`` token with its supplied value."""
    text = load_prompt(name)
    for key, value in values.items():
        text = text.replace("{" + key + "}", value)
    return text
