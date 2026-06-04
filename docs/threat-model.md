# Threat model

Security in this project is **shift-left**: the controls below were built in the
phase that first needed them, not bolted on at the end. Each row names the
threat, its concrete vector in *this* system, and the control plus the file that
implements it.

---

## STRIDE-lite table

| Threat | Vector in this system | Control (where) |
|---|---|---|
| **Prompt injection** (Tampering / EoP) | Web-search results contain `"ignore your instructions"`-style text that a debater or the judge ingests | `security/sanitizer.py` wraps all tool/web output as **untrusted quoted data**, neutralises injection markers, and caps length; the judge never receives raw web text — only relayed debater turns |
| **Secret leakage** (Info disclosure) | API keys end up in git, logs, or error traces | `.env` is git-ignored; `config/secrets.py` resolves keys and never echoes their value in errors; `observability/redaction.py` scrubs every log line; gitleaks pinned in pre-commit |
| **Runaway spend / DoS-on-wallet** (DoS) | Retry storms, large prompts, runaway loops | `gatekeeper/budget.py` + `limiter.py` enforce hard USD / token / call limits; `check()` blocks *before* a limit is crossed, `record()` updates after each call; circuit breaker stops a failing provider |
| **SSRF / malicious egress** (EoP) | Web-search tool coerced into fetching attacker URLs / internal IPs | `security/egress.py`: domain **allowlist**, enforced HTTPS/TLS verification, blocks private/loopback/link-local IPs, rejects redirects to disallowed hosts |
| **Hung / crashed agent** (DoS) | Provider stalls or generates without end | per-request **timeout** in `llm/resilience.py` + `orchestration/watchdog.py` kill-and-restart bounded by `max_restarts` |
| **Offensive / policy-violating output** (Repudiation/abuse) | A debater curses or shouts | `security/moderation.py` content check + per-turn **word cap** from config |
| **Supply-chain** (Tampering) | Compromised or typo-squatted dependency | version-pinned deps in `pyproject.toml` (+ `uv.lock` on `uv sync`) + `pip-audit` + `bandit` in CI/pre-commit |
| **Verdict tie-smuggling** (Tampering) | Model returns equal/null winner to dodge a decision | `protocol/verdict.py` rejects equal scores and null/"tie" winner at the model level; `agents/judge.py` adds a code-level tie-break so a strict winner is always produced |

---

## Trust boundaries

```
   [ user / config ]      [ LLM provider ]        [ open internet ]
          │                      │                       │
          ▼                      ▼                       ▼
   config validation     resilience wrapper        egress allowlist
   (config/schema.py)     (llm/resilience.py)        (security/egress.py)
          │              timeout/retry/breaker             │
          │              gatekeeper check/record           ▼
          │                      │                  sanitizer
          ▼                      ▼              (security/sanitizer.py)
   ─────────────────────  TRUSTED CORE  ──────────────────────
        agents · orchestration · protocol (validated JSON only)
   ────────────────────────────────────────────────────────────
                              │
                              ▼
                    redaction + FIFO logging
                  (observability/*) — secrets scrubbed
```

Three external inputs cross into the trusted core, and each is validated at the
boundary: **user/config** (typed validation), **LLM output** (parsed into the
JSON protocol; the verdict invariant rejects ties), and **web content** (egress
allowlist on the way out, sanitizer on the way in).

---

## Control verification (evidence)

Each control has automated tests and, for Phase 8, a captured live/forced demo:

| Control | Tests | Live/forced demo |
|---|---|---|
| Sanitizer (injection) | `tests/test_sanitizer_injection.py` | `docs/evidence/feature-demos.txt §4` |
| Egress allowlist / SSRF | `tests/test_egress_allowlist.py` | — |
| Moderation / word cap | `tests/test_moderation.py` | — |
| Gatekeeper limits | `tests/test_gatekeeper.py` | `docs/evidence/feature-demos.txt §1` |
| Timeout / retry / breaker | `tests/test_llm_resilience.py` | `docs/evidence/feature-demos.txt §3`, `real-ratelimit-resilience.jsonl` |
| Watchdog kill/restart | `tests/test_watchdog.py` | `docs/evidence/feature-demos.txt §2` |
| No-tie verdict | `tests/test_verdict_no_tie.py` | session-01 verdict (82 vs 78) |
| Judge intervention | `tests/test_judge_intervention.py` | `docs/evidence/feature-demos.txt §5` |
| Secret redaction | `tests/test_redaction.py` | `docs/evidence/security-audit.txt` |

Security tooling status (Phase 8 audit — `docs/evidence/security-audit.txt`):
`bandit` clean, `pip-audit` no known CVEs, full git-history scan confirms no
`.env` or real key was ever committed (only `.env.example` is tracked).
