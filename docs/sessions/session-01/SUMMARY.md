# Session 1 — recorded debate

**Topic:** *Which is better: Barcelona or Real Madrid?*
**Date:** 2026-06-03
**LLM backend:** Groq (judge `llama-3.3-70b-versatile`, debaters `llama-3.1-8b-instant`)
**Web search:** Tavily tool wired but **not invoked** this run — no `SEARCH_API_KEY`
present (see `../../evidence/web-search-smoke.txt`).

## Budget disclosure

This session was run in **budget mode: 5 rounds per side instead of the full 10**,
to stay within Groq's free-tier tokens-per-minute limit. `config.yaml` was also
tuned for rate tolerance (smaller `max_tokens`, longer backoff, higher breaker
threshold and watchdog keep-alive). 10 rounds/side remains the full-format target.

## Result

| | |
|---|---|
| **Winner** | **PRO** (Barcelona) |
| **Scores** | pro **82.0** vs con **78.0** — decisive, no tie |
| **Exchanges** | 5 PRO + 5 CON (mutual response; each rebuttal links the prior relay) |
| **LLM calls** | 11 successful (10 debater turns + 1 verdict); 1 transient 429 weathered |

**Rationale (judge, persuasiveness-only):** *"The PRO side presented a more
cohesive and well-structured argument, effectively using data and studies to
support their claims… While the CON side raised some valid points, their argument
was often more reactive and struggled to gain momentum."*

## Artifacts

- `transcript.json` — full JSON wire record (every message, all 20 entries).
- `transcript.txt` — human-readable exchange (debater turns + judge relays).
- `verdict.txt` — winner, differential scores, rationale.
- `../../evidence/real-ratelimit-resilience.jsonl` — log from an earlier, faster
  attempt that hit Groq 429s and shows the **real** retry → watchdog-restart →
  circuit-breaker chain firing against the live provider.

Reproduce: `python scripts/capture_session.py --rounds 5 --name session-01`
