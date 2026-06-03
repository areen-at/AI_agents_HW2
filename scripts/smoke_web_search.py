"""Live web-search smoke test — the mandatory internet tool (Phase 4.4 / AC-6).

Builds the hardened :class:`WebSearchTool` from real config + ``.env`` and runs
one genuine Tavily query, proving the egress allowlist, gatekeeper accounting,
and sanitizer all engage on real network content. Citations and the
``web_search_ok`` log line are the captured evidence.

Usage::  python scripts/smoke_web_search.py "Barcelona vs Real Madrid titles"
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from debate.bootstrap import build_gatekeeper, build_logger, build_web  # noqa: E402
from debate.config.loader import load_config  # noqa: E402


def main() -> int:
    query = sys.argv[1] if len(sys.argv) > 1 else "Barcelona vs Real Madrid Champions League titles"
    config = load_config(ROOT / "config.yaml", env_path=ROOT / ".env")
    logger = build_logger(config)
    gatekeeper = build_gatekeeper(config)
    tool = build_web(config, gatekeeper, logger)
    if tool is None:
        print("No web tool built (mock provider or missing SEARCH_API_KEY).")
        return 1

    print(
        f"Query: {query!r}\nProvider: {config.search.provider}  "
        f"allowlist={config.search.allowed_domains}\n"
    )
    citations = tool.search(query)
    print(f"Returned {len(citations)} sanitized citation(s):\n")
    for i, c in enumerate(citations, 1):
        print(f"[{i}] {c.title}\n    {c.url}\n    {c.snippet[:200]}...\n")
    print(f"gatekeeper calls recorded: {gatekeeper.budget.calls}")
    return 0 if citations else 2


if __name__ == "__main__":
    raise SystemExit(main())
