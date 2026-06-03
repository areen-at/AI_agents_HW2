# Implementation Plan — Exercise 02: Debate Between Two AI Agents

**Companion to:** `prd.md`
**Approach:** TDD, phased, bottom-up (services → agents → orchestration → interface →
docs), with **security woven through every phase** (shift-left), not bolted on at the end.

---

## Engineering principles (non-negotiable)

- **150-line hard cap per `.py` file.** Enforced in CI / pre-commit. A file approaching
  the cap is a design smell → split by responsibility. This is *the* forcing function for
  small, single-responsibility modules. Prompts, schemas, and assets live **outside** logic
  files. (Blank lines and comments count; aim for ≤120 lines of real code.)
- **Single Responsibility per module.** One reason to change per file.
- **TDD first** with a deterministic `MockLLM` — no network, no key, no spend in tests.
- **Config-driven** — zero magic numbers in code; all tunables in `config.yaml`.
- **No duplication** — shared logic pushed up the hierarchy (`BaseAgent`, `DebaterAgent`).
- **Defense in depth** — never trust external input (LLM output, web content, user input);
  validate at every trust boundary.
- **Least privilege & fail-safe** — secrets scoped narrowly; on ambiguity, deny/halt.
- **Green at every phase** — `ruff`, `bandit`, `pytest`, and the 150-line check all pass.

---

## Threat model (STRIDE-lite) — drives the security work

| Threat | Vector in this system | Control (where) |
|---|---|---|
| **Prompt injection** | Web-search results contain "ignore your instructions" text that a debater/judge ingests | `security/sanitizer.py`: wrap & neutralize tool output, mark as untrusted data, never as instructions; judge never receives raw web text |
| **Secret leakage** | API keys in git, logs, or error traces | `.env` git-ignored; `security/secrets.py` resolves keys; `observability/redaction.py` scrubs logs; gitleaks pre-commit |
| **Runaway spend (DoS-on-wallet)** | Loop/retry storm, large prompts | `gatekeeper/` hard limits (USD/tokens/calls) + circuit breaker |
| **SSRF / malicious egress** | Web-search tool fetching attacker URLs | `security/egress.py`: domain allowlist, TLS verification, no redirects to private IPs |
| **Hung / crashed agent** | Provider stall, infinite generation | per-request timeout + `orchestration/watchdog.py` kill-and-restart |
| **Offensive / policy-violating output** | Debater "shouts" or curses | `security/moderation.py` content check + per-turn word cap |
| **Supply-chain** | Compromised/typo-squatted dependency | pinned deps + `uv.lock` + `pip-audit`/`bandit` in CI |
| **Tampering with verdict (tie smuggling)** | Model returns equal/null winner | `protocol/verdict.py` invariant + code-level tie-break (no-tie guaranteed) |

---

## Security tooling (added to the toolchain)

- **`ruff`** — lint + format.
- **`bandit`** — Python SAST (insecure calls, `eval`, weak crypto, etc.).
- **`pip-audit`** — dependency CVE scanning against `uv.lock`.
- **`gitleaks`** (or `detect-secrets`) — block secrets from entering git history.
- **`pre-commit`** — runs ruff, bandit, gitleaks, and the **150-line check** on every commit.
- **`scripts/check_file_length.py`** — fails if any tracked `.py` exceeds 150 lines
  (also wired as a pre-commit local hook and a CI step). *(Alternative: pylint
  `max-module-lines = 150`.)*

---

## Target repository layout (every `.py` ≤ 150 lines)

```
AI_agents_HW2/
├── pyproject.toml              # UV deps, ruff, pytest, bandit config
├── uv.lock                     # pinned, hash-verified
├── .pre-commit-config.yaml     # ruff + bandit + gitleaks + file-length
├── README.md                   # diagram, prompts, screenshots, session-1 log
├── prd.md
├── plan.md
├── config.yaml                 # all tunables (no hardcoding)
├── .env.example                # secret NAMES only, placeholders
├── .gitignore                  # .env, .venv, logs/, caches
├── docs/
│   ├── architecture.md         # class + layer diagrams
│   └── threat-model.md         # the STRIDE table above, expanded
├── scripts/
│   └── check_file_length.py    # enforces the 150-line cap
├── src/debate/
│   ├── __init__.py
│   ├── __main__.py             # entry → terminal menu (thin)
│   ├── config/
│   │   ├── loader.py           # load + merge yaml/env
│   │   ├── schema.py           # typed config models + validation
│   │   └── secrets.py          # secret resolution + redaction helpers
│   ├── protocol/
│   │   ├── message.py          # Message envelope model
│   │   ├── verdict.py          # Verdict model + NO-TIE invariant
│   │   └── builder.py          # envelope construction helpers
│   ├── observability/
│   │   ├── fifo_logger.py      # FIFO rotation (N files × M lines)
│   │   └── redaction.py        # scrub secrets/PII before logging
│   ├── security/
│   │   ├── sanitizer.py        # neutralize tool/web content (injection containment)
│   │   ├── moderation.py       # offensive-language / policy checks
│   │   └── egress.py           # URL/domain allowlist + TLS + anti-SSRF
│   ├── gatekeeper/
│   │   ├── budget.py           # USD/token/call accounting
│   │   └── limiter.py          # check()/record() + block logic
│   ├── llm/
│   │   ├── base.py             # LLMProvider abstract + Completion type
│   │   ├── resilience.py       # timeout + retry/backoff + circuit breaker
│   │   ├── anthropic.py        # AnthropicProvider
│   │   ├── openai.py           # OpenAIProvider (optional)
│   │   └── mock.py             # MockLLM (deterministic)
│   ├── tools/
│   │   ├── web_search.py       # WebSearchTool (uses egress + sanitizer)
│   │   └── citations.py        # Citation model + parsing
│   ├── prompts/                # ASSETS, not logic — keeps files tiny
│   │   ├── loader.py           # load a prompt template by name
│   │   ├── pro.md
│   │   ├── con.md
│   │   └── judge.md            # topic-BLIND system prompt
│   ├── agents/
│   │   ├── base.py             # BaseAgent (abstract)
│   │   ├── debater.py          # DebaterAgent (abstract): argue/rebut/research
│   │   ├── pro.py              # ProAgent (skill A)
│   │   ├── con.py              # ConAgent (skill B)
│   │   └── judge.py            # JudgeAgent: relay/intervene/verdict
│   ├── orchestration/
│   │   ├── engine.py           # DebateEngine (thin coordinator)
│   │   ├── router.py           # Child→Father→Child relay logic
│   │   ├── round.py            # single-round execution
│   │   ├── transcript.py       # accumulation + persistence
│   │   └── watchdog.py         # keep-alive, kill & restart
│   ├── sdk.py                  # DebateSDK public API
│   └── ui/
│       ├── menu.py             # menu loop / rendering (thin)
│       └── actions.py          # menu actions → SDK
└── tests/
    ├── conftest.py             # fixtures: MockLLM, temp config/logs
    ├── test_config.py
    ├── test_protocol_message.py
    ├── test_verdict_no_tie.py
    ├── test_fifo_logger.py
    ├── test_redaction.py
    ├── test_sanitizer_injection.py
    ├── test_egress_allowlist.py
    ├── test_moderation.py
    ├── test_gatekeeper.py
    ├── test_llm_resilience.py
    ├── test_web_search.py
    ├── test_agents_base.py
    ├── test_debater.py
    ├── test_judge_intervention.py
    ├── test_engine_routing.py  # Child→Father→Child + mutual response
    ├── test_watchdog.py
    ├── test_sdk.py
    └── test_file_length.py      # asserts the 150-line cap holds
```

**Why this shape:** splitting `config`, `protocol`, `gatekeeper`, `llm`, `security`, and
`orchestration` into packages of small files is what keeps every file under 150 lines while
giving each a single responsibility. Prompts become **assets** loaded at runtime, so agent
logic files stay tiny and prompts are reviewable/diffable on their own.

---

## Phase 0 — Bootstrap & safety rails
**Goal:** runnable, linted, secret-safe, length-enforced skeleton.

- Init repo; `pyproject.toml` (deps + `[tool.ruff]`, `[tool.pytest]`, `[tool.bandit]`).
- `.gitignore` (`.env`, `.venv`, `logs/`, caches) **before first commit**.
- `.env.example` (secret **names** only); `config.yaml` (full key set, PRD §5).
- `.pre-commit-config.yaml`: ruff + bandit + gitleaks + **file-length hook**.
- `scripts/check_file_length.py` + `tests/test_file_length.py`.
- Empty package tree + thin `__main__.py` banner.

**Exit:** `uv sync` works; `ruff`, `bandit`, pre-commit, and length check all clean;
`git status` shows no `.env`; banner runs.

---

## Phase 1 — Cross-cutting services
**Goal:** config, protocol, logging, redaction, gatekeeper primitives.

1. **Config** (`config/loader.py`, `schema.py`, `secrets.py`): load+validate YAML+`.env`,
   typed accessors, fail-fast on missing secrets, **never echo secret values**.
2. **Protocol** (`protocol/message.py`, `verdict.py`, `builder.py`): pydantic envelopes
   (PRD §6); `Verdict` enforces **strict-inequality winner, no null/tie** at the model
   level.
3. **Observability** (`observability/fifo_logger.py`, `redaction.py`): FIFO rotation
   (N×M from config); **redaction scrubs API keys/secrets/PII before any line is written**.
4. **Gatekeeper** (`gatekeeper/budget.py`, `limiter.py`): track calls/tokens/USD;
   `check()` blocks before a limit is crossed; `record()` after each call.

**Tests:** config rejects missing keys; message round-trips; **verdict rejects a tie**;
FIFO rolls & deletes oldest; **redaction hides a planted secret**; gatekeeper blocks at limit.

---

## Phase 2 — Security primitives
**Goal:** the trust-boundary controls used by tools and agents. *(New phase — pulled
early so later layers consume them.)*

1. `security/sanitizer.py`: wrap untrusted text (web/tool output) so it is presented to the
   model as **quoted data, never instructions**; strip/escape injection markers; cap length.
2. `security/egress.py`: outbound URL **domain allowlist**, enforce **TLS verification**,
   block private/loopback IPs (anti-SSRF), no auto-following redirects to disallowed hosts.
3. `security/moderation.py`: reject/flag offensive language; enforce the respectful-tone
   policy and per-turn word cap.

**Tests:** `test_sanitizer_injection` (a "ignore previous instructions" payload is
neutralized); `test_egress_allowlist` (off-allowlist/loopback URL rejected);
`test_moderation` (cursing flagged, clean text passes).

---

## Phase 3 — LLM provider layer (SDK-independent)
**Goal:** swappable LLM abstraction with resilience; deterministic mock.

1. `llm/base.py`: `LLMProvider.complete(system, messages, **opts) -> Completion`.
2. `llm/resilience.py`: single wrapper adding **timeout**, **retry+backoff**,
   **circuit breaker**, gatekeeper `check/record`, and redacted logging. *No agent ever
   calls a vendor SDK directly — this is the only choke-point.*
3. `llm/mock.py`: deterministic, scriptable (incl. canned "over-agreement" and "tie"
   outputs for later tests).
4. `llm/anthropic.py` (default) and `llm/openai.py` (optional).

**Tests:** `test_llm_resilience` — timeout handled, retry on transient error, breaker trips,
gatekeeper invoked; MockLLM returns scripted output. (Real providers smoke-tested manually.)

---

## Phase 4 — Web search tool (mandatory)
**Goal:** real internet search, hardened.

- `tools/web_search.py` + `tools/citations.py`: `search(query) -> list[Citation]`,
  routed through `security/egress.py`, results passed through `security/sanitizer.py`,
  timeout + gatekeeper-aware; graceful empty-result degradation (logged).

**Tests:** mocked HTTP → parsed citations; failure → `[]` + log; **all results sanitized**;
off-allowlist host blocked. (One live manual smoke test documented for README.)

---

## Phase 5 — Agent hierarchy (OOP core, no duplication)
**Goal:** the three agents on shared base classes; prompts as assets.

1. `prompts/loader.py` + `pro.md`/`con.md`/`judge.md`: system prompts as templates.
2. `agents/base.py` (`BaseAgent`, abstract): holds `llm`, `logger`, `config`, `agent_id`,
   `role`; `send()` builds JSON envelope, calls LLM (already resilient/gatekept), logs
   (redacted), returns `Message`. Abstract `system_prompt()`/`build_prompt()`.
3. `agents/debater.py` (`DebaterAgent`, abstract): `position`, `skill`, `web` tool;
   `argue()`, `rebut(opp_msg)`, `research()`; enforces word cap + moderation; persona/skill
   injected to guarantee **real opposition** and resist people-pleasing.
4. `agents/pro.py` / `con.py`: differ only by **position** + **distinct skill**.
5. `agents/judge.py` (`JudgeAgent`): **topic-blind**; `relay()`, `intervene(reason)`
   (anti-agreement), `verdict() -> Verdict` with strict-inequality scoring on
   **persuasiveness**.

**Tests:** base produces valid envelope; debater enforces word cap + rebuttal links
opponent id; **judge.verdict never ties** (forced equal-score → tie-break yields a winner);
**judge.intervene** fires on a canned "I totally agree" message.

---

## Phase 6 — Orchestration (the heart)
**Goal:** routed debate loop + resilience, decomposed to stay under 150 lines each.

1. `orchestration/router.py`: enforces **Child → Father → Child**; no direct Pro↔Con path.
2. `orchestration/round.py`: executes one exchange; guarantees **mutual response**
   (feeds opponent's last relayed message, links `rebuts_message_id`).
3. `orchestration/transcript.py`: accumulate + persist full JSON transcript (FIFO logger).
4. `orchestration/engine.py` (`DebateEngine`, thin): wires agents from config, loops
   `rounds_per_side`, ends with `judge.verdict()`.
5. `orchestration/watchdog.py`: keep-alive per turn; on timeout/crash **kill & restart**
   (bounded by `max_restarts`), logged.

**Tests:** `test_engine_routing` — no direct Pro↔Con traffic, all via judge, rebuttals link
correct prior message, exactly `rounds_per_side` per side; `test_watchdog` — hung turn
timed out, killed, restarted, run recovers.

---

## Phase 7 — SDK & interface layers
**Goal:** both ways the tester runs it; interface-agnostic SDK.

1. `sdk.py` (`DebateSDK`): `run_debate(topic=None, rounds=None) -> DebateResult` +
   transcript/verdict accessors. Interface-agnostic (the layer the agent can self-drive).
2. `ui/menu.py` + `ui/actions.py`: keyboard menu —
   `[1] Configure  [2] Run (live)  [3] Transcript  [4] Verdict  [5] Settings  [0] Exit`;
   wraps `DebateSDK` only.
3. `__main__.py`: launches the menu.

**Tests:** `test_sdk` runs a full MockLLM debate → decisive verdict + correct count;
menu smoke-tested with scripted stdin.

---

## Phase 8 — Hardening, real run, audit
**Goal:** production polish + a real recorded session + security sign-off.

- Wire **real** LLM + **real** web search; run a genuine debate (chosen topic).
- Capture **session 1** (JSON + human-readable) and the verdict.
- Screenshots of menu + running debate.
- Demonstrate: gatekeeper block, watchdog restart, timeout, **injection containment**.
- Run `ruff`, `bandit`, `pip-audit`, `gitleaks` clean; confirm **`.env` never in git
  history**; raise coverage on core/security paths.

**Exit:** real session captured; security scans green; all features demonstrable.

---

## Phase 9 — Documentation & submission

- `README.md`: overview + rules of the game (persuasion, no tie, topic-blind judge);
  **architecture + class diagram**; **threat model summary**; UV setup
  (`uv sync`, run menu, run via SDK); **prompts** (Pro/Con/Judge); **screenshots**;
  **full session-1 dialogue log**; engineering notes (timeouts, watchdog, gatekeeper,
  FIFO logging, JSON protocol, **security controls**); budget disclosure if rounds 10→5;
  language note (English/Hebrew).
- Confirm `.env.example` only; repo **public / shared with lecturer**.
- Pair submission: same repo link; each partner submits the PDF in Moodle.

---

## Phase → Requirement / security traceability

| Requirement | Phase |
|---|---|
| JSON protocol, FIFO logging, gatekeeper | 1 |
| Secret redaction / no key leakage | 1, 8 |
| Prompt-injection containment (sanitizer) | 2, 4 |
| Anti-SSRF egress allowlist + TLS | 2, 4 |
| Content moderation / respectful tone | 2, 5 |
| Timeouts / retry / circuit breaker | 3 |
| Real LLM debate (single choke-point) | 3 |
| Mandatory web search | 4 |
| OOP hierarchy, no duplication, ≤150 lines/file | 0, 5, every phase |
| Distinct skills / real opposition | 5 |
| Topic-blind judge | 5 |
| No-tie verdict (code-enforced) | 1, 5 |
| Anti-agreement intervention | 5 |
| Child→Father→Child routing | 6 |
| Mutual response, ≥10 exchanges/side | 6 |
| Watchdog kill/restart | 6 |
| SDK independent of interface | 7 |
| Terminal menu | 7 |
| Secrets safety, UV/pyproject | 0 |
| Ruff + bandit + pip-audit + gitleaks + TDD | every phase |
| Diagram / session log / screenshots | 8–9 |

---

## Commit cadence
One reviewed, **green** commit per sub-component (ruff + bandit + pytest + length check).
Never commit `.env`. Branch off `main`; PR per phase if working as a pair.

---

## Open decisions to confirm before Phase 3
1. **LLM backend:** Anthropic (default), OpenAI, or both behind the abstraction?
2. **Session-1 topic** (e.g., Barcelona vs. Real Madrid).
3. **Web search provider** (which API/key the pair holds) + its **egress allowlist**.
4. **Rounds:** 10 (full) or 5 (budget — disclose in README)?
5. **Config format:** YAML (assumed) vs. TOML.
