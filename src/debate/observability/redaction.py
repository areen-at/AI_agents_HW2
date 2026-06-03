"""Secret/PII scrubbing applied to **every** log line before it is written.

Defence-in-depth: even if a secret reaches a log call, these patterns mask it.
:func:`redact` is the single chokepoint used by the FIFO logger.
"""

from __future__ import annotations

import re

MASK = "[REDACTED]"

# Ordered patterns; each captures a leading label group we keep, then masks
# the secret value. Kept deliberately broad — false positives are acceptable
# in logs, leaked secrets are not.
_PATTERNS: tuple[re.Pattern[str], ...] = (
    # Bearer tokens: "Authorization: Bearer <token>"
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._\-]{8,}"),
    # Provider-style keys: sk-..., sk-ant-..., pk-..., tvly-...
    re.compile(r"\b((?:sk|pk|tvly|rk)-(?:ant-)?)[A-Za-z0-9._\-]{6,}"),
    # key=value / "api_key": "value" style assignments.
    re.compile(
        r"(?i)((?:api[_-]?key|secret|token|password)['\"]?\s*[:=]\s*['\"]?)"
        r"[A-Za-z0-9._\-]{6,}"
    ),
)


def redact(text: str) -> str:
    """Return ``text`` with known secret shapes replaced by :data:`MASK`.

    The captured label/prefix (group 1) is preserved so logs stay readable,
    e.g. ``Bearer [REDACTED]`` or ``api_key=[REDACTED]``.
    """
    if not text:
        return text
    result = text
    for pattern in _PATTERNS:
        result = pattern.sub(lambda m: m.group(1) + MASK, result)
    return result
