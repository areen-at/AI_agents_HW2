"""Capture a real debate session as committed evidence (Phase 8.2).

Runs one full debate through the public :class:`DebateSDK` using whatever
provider ``config.yaml`` selects (Groq + Tavily for the recorded session), then
writes three artefacts to ``docs/sessions/<name>/``:

* ``transcript.json``      — the full JSON wire record (every message).
* ``transcript.txt``       — the human-readable exchange (relays included).
* ``verdict.txt``          — winner, differential scores, and rationale.

Usage::

    python scripts/capture_session.py --rounds 5 --name session-01

Secrets come from ``.env`` via the SDK; none are printed or written here.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from debate.protocol.message import Party  # noqa: E402
from debate.sdk import DebateSDK  # noqa: E402

SESSIONS_DIR = ROOT / "docs" / "sessions"


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Capture a real debate session.")
    p.add_argument("--rounds", type=int, default=None, help="rounds per side override")
    p.add_argument("--topic", type=str, default=None, help="debate topic override")
    p.add_argument("--name", type=str, default="session-01", help="output subdirectory")
    return p.parse_args()


def _verdict_text(verdict: object) -> str:
    return (
        f"WINNER: {verdict.winner.value.upper()}\n"
        f"SCORES: pro={verdict.scores.pro}  con={verdict.scores.con}\n\n"
        f"RATIONALE:\n{verdict.rationale}\n"
    )


def main() -> int:
    args = _parse_args()
    sdk = DebateSDK.from_path(ROOT / "config.yaml", env_path=ROOT / ".env")
    cfg = sdk.config
    print(
        f"Provider={cfg.llm.provider}  topic={args.topic or cfg.debate.topic!r}  "
        f"rounds/side={args.rounds or cfg.debate.rounds_per_side}",
        flush=True,
    )
    result = sdk.run_debate(topic=args.topic, rounds=args.rounds)

    out = SESSIONS_DIR / args.name
    out.mkdir(parents=True, exist_ok=True)
    (out / "transcript.json").write_text(result.transcript.as_json(), encoding="utf-8")
    (out / "transcript.txt").write_text(result.transcript.as_text(), encoding="utf-8")
    (out / "verdict.txt").write_text(_verdict_text(result.verdict), encoding="utf-8")

    pro = result.transcript.count_turns(Party.PRO)
    con = result.transcript.count_turns(Party.CON)
    print(f"\nSaved session to {out}")
    print(_verdict_text(result.verdict))
    print(f"turns: PRO={pro}  CON={con}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
